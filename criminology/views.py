import csv
import json
import logging
import random as rd
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from string import ascii_lowercase

import pandas as pd
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Max, OuterRef, Q, Subquery, Sum, Value
from django.db.utils import IntegrityError
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import AcademicYearForm
from .models import *
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
from django.core.paginator import Paginator
from django.utils import timezone
from io import StringIO






total_qty = 0
gnrt_totals = {}
answer_keys = []
answer_keys_tos = []


def parse_decimal_input(value, field_label, decimal_places=2):
    """Parse and validate decimal input from request data."""
    if value is None:
        return Decimal("0")

    value_str = str(value).strip()
    if value_str == "":
        return Decimal("0")

    try:
        decimal_value = Decimal(value_str)
    except (InvalidOperation, ValueError):
        raise ValidationError(f"Invalid numeric value for {field_label}. Please enter a valid number.")

    if decimal_places is not None and decimal_places >= 0:
        quantize_target = Decimal("1").scaleb(-decimal_places)
        decimal_value = decimal_value.quantize(quantize_target)

    return decimal_value


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)  
            return redirect('homepage')  
        else:
            return render(request, 'authenticate/loginform.html', {'error': 'Invalid username & password'})
    return render(request, 'authenticate/loginform.html')

def logout(request):
    auth_logout(request)
    return redirect('loginpage')





@login_required(login_url='loginpage')
def homepage(request):
    active_year = AcademicYear.objects.filter(status=1).first()
    assessment_records = AssessmentRecordsDashboard.objects.filter(academic_year=active_year)
    total = Questionnaire.objects.all().count()
    restrictedquestion = Questionnaire.objects.filter(status=1)
    restricted_counts = Questionnaire.objects.filter(status=1).count()

    status_value = request.session.get('status_value')

    restricted_remembering = Questionnaire.objects.filter(status=1, category__category="remembering").count()
    restricted_understanding = Questionnaire.objects.filter(status=1, category__category="understanding").count()
    restricted_creating = Questionnaire.objects.filter(status=1, category__category="creating").count()
    restricted_evaluating = Questionnaire.objects.filter(status=1, category__category="evaluating").count()
    restricted_applying = Questionnaire.objects.filter(status=1, category__category="applying").count()
    restricted_analyzing = Questionnaire.objects.filter(status=1, category__category="analyzing").count()

    enrolled_students_count = Students.objects.filter(academic_year__in=[active_year]).count()
    categoryTos = CategoriesCountPercentage.objects.filter(academic_year=active_year).first()

    if categoryTos:
        overall_percentages = {
            'remembering_percentage': categoryTos.calculate_remembering_percentage,
            'creating_percentage': categoryTos.calculate_creating_percentage,
            'understanding_percentage': categoryTos.calculate_understanding_percentage,
            'applying_percentage': categoryTos.calculate_applying_percentage,
            'analyzing_percentage': categoryTos.calculate_analyzing_percentage,
            'evaluating_percentage': categoryTos.calculate_evaluating_percentage,
            'average': categoryTos.calculate_overall_percentage,
        }
    else:
        overall_percentages = {
            'remembering_percentage': 0,
            'creating_percentage': 0,
            'understanding_percentage': 0,
            'applying_percentage': 0,
            'analyzing_percentage': 0,
            'evaluating_percentage': 0,
            'average': 0,
        }

    subject_count_percentage_data = SubjectCountPercentage.objects.filter(academic_year=active_year)
    subject_data = [
        {
            'subject_code': subject.subject.subject_code,
            'percentage': subject.calculate_cor_percentage()
        }
        for subject in subject_count_percentage_data
    ]

    subject_codes = [data['subject_code'] for data in subject_data]
    subject_percentages = [data['percentage'] for data in subject_data]

    context = {
        'total': total,
        'enrolled_students_count': enrolled_students_count,
        'assessment_records': assessment_records,
        'overall_percentages': overall_percentages,
        'subject_codes': subject_codes,
        'subject_percentages': subject_percentages,
        'restrictedquestion': restrictedquestion,
        'restricted_remembering': restricted_remembering,
        'restricted_understanding': restricted_understanding,
        'restricted_creating': restricted_creating,
        'restricted_evaluating': restricted_evaluating,
        'restricted_applying': restricted_applying,
        'restricted_analyzing': restricted_analyzing,
        'restricted_counts': restricted_counts,
        'overall_percentage': categoryTos.calculate_overall_percentage if categoryTos else 0,
        'status_value': status_value,
        'subject_data': subject_data 
    }

    return render(request, 'assets/dashboard.html', context)





@csrf_exempt
def endpoint(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        status_value = data.get('status')
        
        
        request.session['status_value'] = status_value
            
        return JsonResponse({'message': 'Success', 'status': status_value})

    return JsonResponse({'error': 'Invalid request'}, status=400)



def restrictquestionremove(request, id):

    question = get_object_or_404(Questionnaire, id=id)

    question.status = 0

    question.save()

    return redirect(reverse('restricted_list'))

# ==============QUESTIONNAIRES===============

@login_required(login_url='loginpage')
def questionnaires(request):
    active_academic_year = AcademicYear.objects.filter(status=1).first()

    # Define 'category' outside the conditional block
    if active_academic_year is None:
        representative_records = []
        representative_records_assessment = []
        filtered_subjects = Subject.objects.all()
        category = Category.objects.none()  # This ensures 'category' is always defined
    else:
        subjects = Subject.objects.all()
        category = Category.objects.all()

        existing_entries = TableOfSpecification.objects.filter(academic_year=active_academic_year)
        existing_subject_ids = existing_entries.values_list('subject_id', flat=True)

        filtered_subjects = subjects.exclude(id__in=existing_subject_ids)

        table_of_specification = (
            TableOfSpecification.objects
            .filter(academic_year=active_academic_year)
            .values('group_id')
            .annotate(max_id=Max('id'))
        )

        excluded_group_ids = AnswerKeyTableOfSpecification.objects.values_list('tos_exam_id', flat=True)

        representative_records = TableOfSpecification.objects.filter(
            id__in=[entry['max_id'] for entry in table_of_specification]
        ).exclude(
            group_id__in=excluded_group_ids 
        ).order_by('-id')

        assessment_datas = (
            Assessment.objects
            .filter(academic_year=active_academic_year)
            .values('assessment_id')
            .annotate(max_id=Max('id'))
        )

        representative_records_assessment = Assessment.objects.filter(
            id__in=[entry['max_id'] for entry in assessment_datas]
        ).order_by('-id')

        answer_key_assessment_ids = AnswerKeyAssessment.objects.values_list('assessment_exam_id', flat=True).distinct()
        representative_records_assessment = representative_records_assessment.exclude(
            assessment_id__in=answer_key_assessment_ids
        )

    q = request.GET.get('q', '')

    if q:
        questionnaires = Questionnaire.objects.filter(description__icontains=q).order_by('-id')[:60]
    else:
        questionnaires = Questionnaire.objects.all().order_by('-id')[:60]

    context = {
        'questionnaires': questionnaires,
        'category': category,
        'q': q,
        'table_of_specification': representative_records,
        'assessment': representative_records_assessment
    }

    return render(request, 'assets/questionnaires.html', context)



@login_required(login_url='loginpage')
def questionnairescreate(request):
    subjects = Subject.objects.all()
    category = Category.objects.all()
        
    context = {
        'subjects': subjects,
        'category': category,
    }
    return render(request, 'assets/questionnaires_create.html', context)


def addquestion(request):
    if request.method == 'POST':
        description_compare = request.POST.get('descriptioncreate').strip().lower().replace(' ', '')
        subject_id = request.POST.get('subjectcreate')
        category_id = request.POST.get('categorycreate')
        topic_id = request.POST.get('topiccreate')
        subtopic_id = request.POST.get('subtopiccreate')
        description = request.POST.get('descriptioncreate')
        correct_answer = request.POST.get('correctanscreate')
        distractor1 = request.POST.get('distructorcreate1')
        distractor2 = request.POST.get('distructorcreate2')
        distractor3 = request.POST.get('distructorcreate3')

        subject = Subject.objects.get(id=subject_id)
        category = Category.objects.get(id=category_id)
        topic = Topic.objects.get(id=topic_id)
        subtopic = Subtopic.objects.get(id=subtopic_id)

        question_from_db = Questionnaire.objects.filter(description=description).first()

        if question_from_db:
            qq = question_from_db.description.strip().lower().replace(' ', '')

            if description_compare == qq:
                messages.error(request, 'This question already exists!')
            else:
                datas = Questionnaire.objects.create(
                    subject=subject,
                    category=category,
                    topic=topic,
                    subtopic=subtopic,
                    description=description,
                    correct_answer=correct_answer,
                    distructor1=distractor1,
                    distructor2=distractor2,
                    distructor3=distractor3
                )
                datas.save()
                messages.success(request, 'Added successfully!')
        else:

            datas = Questionnaire.objects.create(
                subject=subject,
                category=category,
                topic=topic,
                subtopic=subtopic,
                description=description,
                correct_answer=correct_answer,
                distructor1=distractor1,
                distructor2=distractor2,
                distructor3=distractor3
            )
            datas.save()
            messages.success(request, 'Added successfully!')

        return redirect(reverse('questionnairescreate'))
    else:
        pass



def restrictquestion(request, id):
    question = get_object_or_404(Questionnaire, id=id)
    question.status = 1
    question.save()
    messages.success(request, 'Restricted succesfully!')
    return redirect(reverse('questionnaires'))


def delete(request, id):
    q = get_object_or_404(Questionnaire, id=id)
    q.delete()
    return redirect(reverse('questionnaires'))


@login_required(login_url='loginpage')
def update(request, id):
    q = get_object_or_404(Questionnaire, id=id)
    subjects = Subject.objects.all()
    categories = Category.objects.all()
    topics = Topic.objects.filter(subject_topic=q.subject)
    subtopics = Subtopic.objects.filter(topic_subtopic=q.topic)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if 'subject_id' in request.GET:
            subject_id = request.GET.get('subject_id')
            topics = Topic.objects.filter(subject_topic_id=subject_id)
            topics_data = list(topics.values('id', 'topic_name'))
            return JsonResponse({'topics': topics_data})
        elif 'topic_id' in request.GET:
            topic_id = request.GET.get('topic_id')
            subtopics = Subtopic.objects.filter(topic_subtopic_id=topic_id)
            subtopics_data = list(subtopics.values('id', 'subtopic_name'))
            return JsonResponse({'subtopics': subtopics_data})
    
    context = {
        'q': q,
        'subjectsup': subjects,
        'categories': categories,
        'topics': topics,
        'subtopics': subtopics
    }
    return render(request, 'assets/questionnaires_update.html', context)





def updatequestion(request, id):
    if request.method == 'POST':
        try:
            a = request.POST.get('subjectupdate')
            b = request.POST.get('topicupdate')
            c = request.POST.get('subtopicupdate')
            d = request.POST.get('categoryupdate')
            e = request.POST.get('descriptionupdate')
            f = request.POST.get('correctansupdate')
            g = request.POST.get('distructorupdate1')
            h = request.POST.get('distructorupdate2')
            i = request.POST.get('distructorupdate3')

            subject = get_object_or_404(Subject, id=a)
            category = get_object_or_404(Category, id=d)
            topic = get_object_or_404(Topic, id=b)
            subtopic = get_object_or_404(Subtopic, id=c)

            mem = get_object_or_404(Questionnaire, id=id)
            mem.subject = subject
            mem.category = category
            mem.topic = topic
            mem.subtopic = subtopic
            mem.description = e
            mem.correct_answer = f
            mem.distructor1 = g
            mem.distructor2 = h
            mem.distructor3 = i

            mem.save()
            messages.success(request, 'Questionnaire updated successfully!')
            return redirect(reverse('questionnaires'))
        except Exception as ex:
            messages.error(request, f'Error updating questionnaire: {ex}')
            return redirect(reverse('update', args=[id]))
    else:
        return redirect(reverse('update', args=[id]))
    


def get_correct_choice_letter_tos(question, choices):
    for index, choice in enumerate(choices):
        if choice == question.correct_answer:
            return chr(65 + index)  


@login_required(login_url='loginpage')
def print_questionnaire(request, group_id):
    global answer_keys_tos
    tos_entries = TableOfSpecification.objects.filter(group_id=group_id)

    request.session['group_id'] = group_id

    active_year = AcademicYear.objects.get(status=1)
    
    generated_questions = []
    answer_keys_tos = []
    category_counts = {category: 0 for category in [
        'understanding',
        'remembering',
        'analyzing',
        'creating',
        'evaluating',
        'applying',
    ]}

    topic_counts = {}
    subtopic_counts = {}
    subject_name = None

    for entry in tos_entries:
        row_id = entry.row_id

        for category in category_counts.keys():
            count = getattr(entry, category)

            subtopic = get_object_or_404(Subtopic, id=entry.subtopic_id)
            topic = get_object_or_404(Topic, id=entry.topic_id)

            try:
                subject = Subject.objects.get(id=entry.subject_id)
            except Subject.DoesNotExist:
                messages.error(request, f"Subject with id {entry.subject_id} does not exist.")
                logger.error(f"Subject with id {entry.subject_id} does not exist.")
                subject = None  

            if subject is not None:
                if subject_name is None:
                    subject_name = subject.subject_name

                if topic.topic_name not in topic_counts:
                    topic_counts[topic.topic_name] = 0
                if subtopic.subtopic_name not in subtopic_counts:
                    subtopic_counts[subtopic.subtopic_name] = 0

                if category in category_counts:
                    available_questions = Questionnaire.objects.filter(
                        status=0,
                        subject=subject,
                        topic=topic,
                        subtopic=subtopic,
                        category__category=category
                    ).order_by('?')[:count]

                    for question in available_questions:
                        choices = [
                            question.correct_answer,
                            question.distructor1,
                            question.distructor2,
                            question.distructor3,
                        ]
                        rd.shuffle(choices)

                        correct_choice_letter = get_correct_choice_letter_tos(question, choices)

                        lettered_choices = [(chr(65 + i), choice) for i, choice in enumerate(choices)]

                        generated_questions.append({
                            'id': question.id,
                            'subject': subject.subject_name,
                            'topic': topic.topic_name,
                            'subtopic': subtopic.subtopic_name,
                            'category': category,
                            'description': question.description,
                            'choices': lettered_choices,
                            'correct_choice_letter': correct_choice_letter,
                            'correct_answer': question.correct_answer,
                        })

                        category_counts[category] += 1
                        topic_counts[topic.topic_name] += 1
                        subtopic_counts[subtopic.subtopic_name] += 1

                        answer_keys_toss = AnswerKeyTableOfSpecification(
                            academic_year=active_year,
                            tableofspecification=entry,
                            question=question,
                            subject=subject,
                            category=category,
                            number=len(generated_questions),
                            tos_exam_id=group_id,
                            row_id=row_id, 
                            a=lettered_choices[0][1],
                            b=lettered_choices[1][1],
                            c=lettered_choices[2][1],
                            d=lettered_choices[3][1],
                            correct_choice=correct_choice_letter,
                            correct_answer=question.correct_answer,
                            topic=topic, 
                            subtopic=subtopic
                        )
                        answer_keys_tos.append(answer_keys_toss)

    primary_keys = [question['id'] for question in generated_questions]
    total_generated_questions = len(generated_questions)

    overall_total = sum(category_counts.values())

    context = {
        'generated_questions': generated_questions,
        'primary_keys': primary_keys,
        'total_generated_questions': total_generated_questions,
        'overall_total': overall_total,
        'category_counts': category_counts,
        'group_id': group_id,
        'subject_name': subject_name, 
        'topic_counts': topic_counts,
        'subtopic_counts': subtopic_counts,
    }

    return render(request, 'assets/questionnaire_generate_tos.html', context)

@csrf_exempt
def save_answer_key_tos(answer_keys_tos):
    for answer_key in answer_keys_tos:
        answer_key.save()

def save_answer_key_toss(request):
    global answer_keys_tos

    questions = len(answer_keys_tos)
    group_id = request.session.get('group_id', [])

    if questions == 100:
        save_answer_key_tos(answer_keys_tos)
        answer_keys_tos = []
        return redirect(reverse('questionnaires')) 
    else:
        messages.error(request, "Save failed. Only 100 questions are required to proceed.")
        return redirect(reverse('print_questionnaire', args=[group_id]))

@login_required(login_url='loginpage')
def print_questionnaire_view_table(request, group_id):
    tos_entries = TableOfSpecification.objects.filter(group_id=group_id)
    generated_question_ids = []
    topics = {}

    for entry in tos_entries:
        for category in ['understanding', 'remembering', 'analyzing', 'creating', 'evaluating', 'applying']:
            count = getattr(entry, category)

            subtopic = get_object_or_404(Subtopic, id=entry.subtopic_id)
            topic = get_object_or_404(Topic, id=entry.topic_id)
            subject = get_object_or_404(Subject, id=entry.subject_id)

            available_questions = Questionnaire.objects.filter(
                subject=subject,
                topic=topic,
                subtopic=subtopic,
                category__category=category
            ).order_by('?')[:count]

            for question in available_questions:
                generated_question_ids.append(question.id)

            if topic.id not in topics:
                topics[topic.id] = {
                    'topic_name': topic.topic_name,
                    'totals': {cat: 0 for cat in ['remembering', 'understanding', 'applying', 'analyzing', 'evaluating', 'creating']},
                    'subtopics': {},
                }

            topics[topic.id]['totals'][category] += count 

            if subtopic.id not in topics[topic.id]['subtopics']:
                topics[topic.id]['subtopics'][subtopic.id] = {
                    'subtopic_name': subtopic.subtopic_name,
                    'totals': {cat: 0 for cat in ['remembering', 'understanding', 'applying', 'analyzing', 'evaluating', 'creating']}
                }

            topics[topic.id]['subtopics'][subtopic.id]['totals'][category] += count

    for topic in topics.values():
        topic['total_generated'] = sum(topic['totals'].values())
        for subtopic in topic['subtopics'].values():
            subtopic['total_generated'] = sum(subtopic['totals'].values())

    context = {
        'primary_keys': generated_question_ids,
        'total_generated_questions': len(generated_question_ids),
        'group_id': group_id,
        'topics': topics.values()
    }

    return render(request, 'assets/questionnaire_generate_viewtable_tos.html', context)























@login_required(login_url='loginpage')
def print_assessment(request, assessment_id):
    global answer_keys
    assessments = Assessment.objects.filter(assessment_id=assessment_id)
    active_year = AcademicYear.objects.get(status=1)
    period = assessments.first()
    request.session['assessment_id'] = assessment_id 

    answer_keys = []

    generated_questions = []
    category_counts = {
        'remembering': 0,
        'understanding': 0,
        'applying': 0,
        'analyzing': 0,
        'evaluating': 0,
        'creating': 0,
    }

    levels = ['remembering', 'understanding', 'applying', 'analyzing', 'evaluating', 'creating']
    
    answer_data = [] 
    
    question_number = 1 

    for assessment in assessments:
        subject = assessment.subject
        topic = assessment.topic
        competency = assessment.competencies

        for level in levels:
            num_questions = getattr(assessment, level)

            if num_questions > 0:
                available_questions = Questionnaire.objects.filter(
                    subject=subject,
                    category__category=level,
                    topic=topic,
                    subtopic = competency,
                    status=0
                ).order_by('?')[:num_questions]

                for question in available_questions:
                    choices = [
                        question.correct_answer,
                        question.distructor1,
                        question.distructor2,
                        question.distructor3,
                    ]

                    rd.shuffle(choices)
                    correct_choice_letter = get_correct_choice_letter(question, choices)

                    answer_data.append({
                        'assessment_id': assessment_id,
                        'question_id': question.id,
                        'number': question_number,
                        'a': choices[0],
                        'b': choices[1],
                        'c': choices[2],
                        'd': choices[3],
                        'correct_choice': correct_choice_letter,
                        'correct_answer': question.correct_answer,
                    })

                    lettered_choices = [(chr(65 + i), choice) for i, choice in enumerate(choices)]

                    generated_questions.append({
                        'id': question.id,
                        'subject': subject.subject_name,
                        'topic': question.topic.topic_name,
                        'subtopic': question.subtopic.subtopic_name,
                        'category': level,
                        'description': question.description,
                        'choices': lettered_choices,
                        'correct_answer': question.correct_answer,
                    })

                    answer_key = AnswerKeyAssessment(
                        academic_year = active_year,
                        assessment=assessment,
                        question=question,
                        assessment_exam_id=assessment_id,
                        a=lettered_choices[0][1],
                        b=lettered_choices[1][1],
                        c=lettered_choices[2][1],
                        d=lettered_choices[3][1],
                        number=question_number,
                        correct_choice=correct_choice_letter,
                        correct_answer=question.correct_answer,
                        category=level,
                        subject=subject
                    )
                    answer_keys.append(answer_key)

                    category_counts[level] += 1
                    question_number += 1 

    total_generated_questions = len(generated_questions)
    overall_total = sum(category_counts.values())

    context = {
        'generated_questions': generated_questions,
        'total_generated_questions': total_generated_questions,
        'overall_total': overall_total,
        'category_counts': category_counts,
        'assessment_id': assessment_id,
        'subject_name': assessments.first().subject.subject_name,
        'assessments': assessments,
        'period' : period,
        'answer_data': json.dumps(answer_data),
    }

    return render(request, 'assets/questionnaire_generate_assessment.html', context)


















def get_correct_choice_letter(question, choices):
    """ Returns the correct choice letter (A, B, C, or D) based on the correct answer """
    for i, choice in enumerate(choices):
        if choice == question.correct_answer:
            return chr(65 + i)
        
def save_answer_keys(answer_keys):
    for answer_key in answer_keys:
        answer_key.save()

def save_answer_key(request):
    global answer_keys
    questions = len(answer_keys)
    assessment_id = request.session.get('assessment_id', [])
    
    if questions == 100:
        save_answer_keys(answer_keys)
        answer_keys = []
        return redirect(reverse('questionnaires'))
    else:
        messages.error(request, "Save failed. Only 100 questions are required to proceed.")
        return redirect(reverse('print_assessment', args=[assessment_id]))



def export_answerkey(request, assessment_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="export_answer_key.csv"'

    writer = csv.writer(response)
    writer.writerow(['Key Letter', 'Question Number', 'Response/Mapping','Point Value', 'Tags'])

    answer_keys = AnswerKeyAssessment.objects.filter(assessment_exam_id= assessment_id)

    for answer_key in answer_keys:
        writer.writerow([
            'A',  
            answer_key.number, 
            answer_key.correct_choice.upper(), 
            1,
            '' 
        ])

    return response


@csrf_exempt
def export_answerkey_tos(request, exam_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="export_answer_key_qualifying.csv"'

    writer = csv.writer(response)
    writer.writerow(['Key Letter', 'Question Number', 'Response/Mapping','Point Value', 'Tags'])

    answer_keys = AnswerKeyTableOfSpecification.objects.filter(tos_exam_id= exam_id)

    for answer_key in answer_keys:
        writer.writerow([
            'A',  
            answer_key.number, 
            answer_key.correct_choice.upper(), 
            1,
            '' 
        ])

    return response



@login_required(login_url='loginpage')
def print_questionnaire_view_table_assessment(request, assessment_id):
    assessments = Assessment.objects.filter(assessment_id=assessment_id)
    if not assessments:
        messages.error(request, "No assessments found for the given ID.")
        return redirect(reverse('assessment'))

    
    subjects = Subject.objects.all()

    context = {
        "assessments": assessments,
        "subjects": subjects,
    }

    return render(request, 'assets/questionnaire_generate_viewtable_assessment.html', context)


def get_unique_assessments():
    active_year = AcademicYear.objects.filter(status=1).first()
    assessments = AnswerKeyAssessment.objects.filter(academic_year=active_year).order_by('assessment_exam_id')
    unique_assessments = {}
    for assessment in assessments:
        if assessment.assessment_exam_id not in unique_assessments:
            unique_assessments[assessment.assessment_exam_id] = assessment
    return list(unique_assessments.values())

def get_unique_table_of_specifications():
    active_year = AcademicYear.objects.filter(status=1).first()
    table_of_specifications = AnswerKeyTableOfSpecification.objects.filter(academic_year=active_year).order_by('tos_exam_id')
    unique_tos = {}
    for tos in table_of_specifications:
        if tos.tos_exam_id not in unique_tos:
            unique_tos[tos.tos_exam_id] = tos
    return list(unique_tos.values())

@login_required(login_url='loginpage')
def print_final_nav(request):
    assessment = get_unique_assessments()
    table_of_specification = get_unique_table_of_specifications()

    context = {'assessment': assessment,
               'table_of_specification': table_of_specification}

    return render(request, 'assets/questionnaire_print.html', context)



@login_required(login_url='loginpage')
def print_generated_assessment(request, assessment_exam_id):
    assessment = AnswerKeyAssessment.objects.filter(assessment_exam_id=assessment_exam_id)

    paginator = Paginator(assessment, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    exam_id = assessment.first().assessment_exam_id if assessment.exists() else None

    context = {
        'page_obj': page_obj,
        'exam_id': exam_id,
        'assessment_exam_id': assessment_exam_id, 
    }

    return render(request, 'assets/questionnaire_print_generated_assessment.html', context)



def print_generated_tableOfSpecification(request, tos_exam_id):
    tos = AnswerKeyTableOfSpecification.objects.filter(tos_exam_id=tos_exam_id)

    paginator = Paginator(tos, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    exam_id = tos.first().tos_exam_id if tos.exists() else None

    context = {
        'page_obj': page_obj,
        'exam_id': exam_id,
        'tos_exam_id': tos_exam_id, 
    }

    return render(request, 'assets/questionnaire_print_generated_tos.html', context)



# ==============MODULES===============

@login_required(login_url='loginpage')
def modulessubject(request):
    query = request.GET.get('q', '')
    if query:
        subjects = Subject.objects.filter(subject_name__icontains=query)
    else:
        subjects = Subject.objects.all().order_by('-id')
    
    context = {'subjects': subjects}
    return render(request, 'assets/masterfilesubject.html', context)


@login_required(login_url='loginpage')
def modulestopic(request):
    query = request.GET.get('q', '')
    if query:
        topics = Topic.objects.filter(topic_name__icontains=query)
    else:
        topics = Topic.objects.all().order_by('-id')
    
    subjects = Subject.objects.all()
    context = {'topics': topics,
               'subjects': subjects}
    return render(request, 'assets/masterfilesubject_topic.html', context)


@login_required(login_url='loginpage')
def modulessubtopic(request):
    query = request.GET.get('q', '')
    if query:
        subtopics = Subtopic.objects.filter(subtopic_name__icontains=query)
    else:
        subtopics = Subtopic.objects.all().order_by('-id')
    
    topic = Topic.objects.all()
    subjects = Subject.objects.all()
    context = {
        'subtopic': subtopics,
        'topic': topic,
        'subjects': subjects 
    }
    return render(request, 'assets/masterfilesubject_subtopic.html', context)



@login_required(login_url='loginpage')
def modules_create_subject(request):
    return render(request, 'partials/modulescreatesubject.html')

@login_required(login_url='loginpage')
def modules_create_topic(request):
    subjects = Subject.objects.all()
    context = {'subjects' : subjects}
    return render(request, 'partials/modulescreatetopic.html',context)

@login_required(login_url='loginpage')
def modules_create_subtopic(request):
    topics = Topic.objects.all()
    context = {'topics' : topics}
    return render(request, 'partials/modulescreatesubtopic.html',context)


def modules_create_subject_final(request):
    if request.method == 'POST':
        subject_name_modules = request.POST.get('subject_name_modules')
        subject_code_modules = request.POST.get('subject_code_modules')
        subject_pw_modules = request.POST.get('subject_pw_modules')

        datas = Subject.objects.create(
            subject_name=subject_name_modules,
            subject_code=subject_code_modules,
            subject_pw=subject_pw_modules,
        )
        datas.save()
        messages.success(request, 'Added succesfully!')
        return redirect(reverse('modulessubject'))
    else:
        pass

def modules_create_topic_final(request):
    if request.method == 'POST':
        subject_topic_modules_id = request.POST.get('subject_topic_modules')
        topic_name_modules = request.POST.get('topic_name_modules')

        subject_topic_modules = get_object_or_404(Subject, id=subject_topic_modules_id)

        datas = Topic.objects.create(
            subject_topic=subject_topic_modules,
            topic_name=topic_name_modules,
        )
        datas.save()
        messages.success(request, 'Added successfully!')
        return redirect(reverse('modulestopic'))
    else:
        pass

def modules_create_subtopic_final(request):
    if request.method == 'POST':
        topic_subtopic_modules_id = request.POST.get('topic_subtopic_modules')
        subtopic_name_modules = request.POST.get('subtopic_name_modules')

        if not topic_subtopic_modules_id or not subtopic_name_modules:
            messages.error(request, 'All fields are required.')
            return redirect(reverse('modules_create_subtopic'))

        try:
            topic_subtopic_modules = get_object_or_404(Topic, id=topic_subtopic_modules_id)
        except Topic.DoesNotExist:
            messages.error(request, 'The specified topic does not exist.')
            return redirect(reverse('modules_create_subtopic'))

        Subtopic.objects.create(
            topic_subtopic=topic_subtopic_modules,
            subtopic_name=subtopic_name_modules,
        )
        messages.success(request, 'Subtopic added successfully!')
        return redirect(reverse('modulessubtopic'))

    return redirect(reverse('modules_create_subtopic'))


@login_required(login_url='loginpage')
def modulessubjectupdate(request, pk):
    subject = get_object_or_404(Subject, id=pk)
    context = {'subject' : subject}
    return render(request, 'assets/masterfilesubjectupdate.html', context)


@login_required(login_url='loginpage')
def modulessubjectdelete(request, pk):
    s = get_object_or_404(Subject, id=pk)
    s.delete()
    return redirect(reverse('modulessubject'))


@login_required(login_url='loginpage')
def modulestopicupdate(request, pk):
    topic = get_object_or_404(Topic, id=pk)
    subjects = Subject.objects.all()
    context = {'topic': topic, 
               'subjects': subjects}
    return render(request, 'assets/masterfilesubject_topicupdate.html', context)


@login_required(login_url='loginpage')
def modulessubtopicupdate(request, pk):
    subtopic = get_object_or_404(Subtopic, id=pk)
    topics = Topic.objects.all()
    context = {'topics': topics, 
               'subtopic': subtopic}
    return render(request, 'assets/masterfilesubject_subtopicupdate.html', context)


def modulessubjectupdatefinal(request, pk):
    if request.method == 'POST':
        
        subjectname = request.POST.get('subject_name_modules')
        subject_code = request.POST.get('subject_code_modules')
        subject_pw = request.POST.get('subject_pw_modules')

        subject = get_object_or_404(Subject, id=pk)

        subject.subject_name = subjectname
        subject.subject_code = subject_code
        subject.subject_pw = subject_pw
        
        subject.save()
        messages.success(request, 'Subject updated successfully!')
        return redirect(reverse('modulessubject'))


@login_required(login_url='loginpage')
def modulestopicupdatefinal(request, pk):
    if request.method == 'POST':
        topicname = request.POST.get('subject_code_modules')
        subject_topic_id = request.POST.get('topic_name_modules')

        topic = get_object_or_404(Topic, id=pk)
        subject_topic = get_object_or_404(Subject, id=subject_topic_id)

        topic.topic_name = topicname
        topic.subject_topic = subject_topic
        
        topic.save()
        messages.success(request, 'Topic updated successfully!')
        return redirect(reverse('modulestopic'))

    return render(request, 'assets/masterfilesubject_topicupdate.html', {'topic': topic, 'subjects': Subject.objects.all()})



def modulestopicdelete(request, pk):
    t = get_object_or_404(Topic, id=pk)
    t.delete()
    return redirect(reverse('modulestopic'))


def modulessubtopicdelete(request, pk):
    s = get_object_or_404(Subtopic, id=pk)
    s.delete()
    return redirect(reverse('modulessubtopic'))



@login_required(login_url='loginpage')
def modulessubtopicupdatefinal(request, pk):
    subtopic = get_object_or_404(Subtopic, id=pk)

    if request.method == 'POST':
        subtopic_name_modules = request.POST.get('subtopic_name_modules')
        topic_subtopic_name_modules = request.POST.get('topic_subtopic_name_modules')

        topic_subtopic = get_object_or_404(Topic, id=topic_subtopic_name_modules)

        subtopic.subtopic_name = subtopic_name_modules
        subtopic.topic_subtopic = topic_subtopic
        
        subtopic.save()
        messages.success(request, 'Subtopic updated successfully!')
        return redirect(reverse('modulessubtopic'))

    return render(request, 'assets/masterfilesubject_subtopicupdate.html', {'subtopic': subtopic, 'topics': Topic.objects.all()})

# ==============MASTERFILE===============


@login_required(login_url='loginpage')
def academic_year(request):
    query = request.GET.get('q')
    if query:
        academic_year = AcademicYear.objects.filter(
            Q(year_series__icontains=query) |
            Q(period__icontains=query)
        ).order_by('-id')
    else:
        academic_year = AcademicYear.objects.all().order_by('-id')

    context = {'academic_year': academic_year}

    return render(request, 'assets/masterfileacademicyear.html', context)


@login_required(login_url='loginpage')
def academicyearcreate(request):
    form = AcademicYearForm()

    if request.method == 'POST':
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            academic_year = form.cleaned_data['academic_year']
            period = request.POST.get('period')
            status = int(request.POST.get('activestatus')) 

           
            if status == 1:
                
                AcademicYear.objects.filter(status=1).update(status=0)

            new_academic_year = AcademicYear(
                year_series=academic_year,
                period=period,
                status=status
            )
            new_academic_year.save()

            return redirect('academic_year')  
    else:
        form = AcademicYearForm()
    
    context = {'form': form}
    return render(request, 'assets/masterfileacademicyearcreate.html', context)

@login_required(login_url='loginpage')
def academicyearupdate(request, pk):
    academic_year = get_object_or_404(AcademicYear, id=pk)

    if request.method == "POST":
        new_status = int(request.POST.get("activestatusupdate")) 
        new_period = request.POST.get("periodupdate")

        if new_status == 1:
            AcademicYear.objects.filter(status=1).exclude(id=pk).update(status=0)

        academic_year.status = new_status
        academic_year.period = new_period
        academic_year.save()

        messages.success(request, 'Academic year updated successfully!')
        return redirect('academic_year')

    context = {'academic_year': academic_year}
    return render(request, 'assets/masterfileacademicyearupdate.html', context)



@login_required(login_url='loginpage')
def table_of_specification(request):
    query = request.GET.get('q')
    active_academic_year = AcademicYear.objects.filter(status=1).first()
    
    if active_academic_year is None:
        representative_records = []
        filtered_subjects = Subject.objects.all()
    else:
        subjects = Subject.objects.all()
        existing_entries = TableOfSpecification.objects.filter(academic_year=active_academic_year)
        existing_subject_ids = existing_entries.values_list('subject_id', flat=True)
        filtered_subjects = subjects.exclude(id__in=existing_subject_ids)

        if query:
            table_of_specification = (
                TableOfSpecification.objects
                .filter(
                    Q(academic_year=active_academic_year) &
                    (Q(group_id__icontains=query) |
                     Q(subject__subject_name__icontains=query) |
                     Q(topic__topic_name__icontains=query))
                )
                .values('group_id')
                .annotate(max_id=Max('id'))
            )
        else:
            table_of_specification = (
                TableOfSpecification.objects
                .filter(academic_year=active_academic_year)
                .values('group_id')
                .annotate(max_id=Max('id'))
            )
        
        representative_records = TableOfSpecification.objects.filter(id__in=[entry['max_id'] for entry in table_of_specification]).order_by('-id')
    
    context = {'subjects': filtered_subjects, 'table_of_specification': representative_records, 'q': query}
    return render(request, 'assets/masterfiletos.html', context)


def table_of_specification_delete(request, group_id):
    TableOfSpecification.objects.filter(group_id=group_id).delete()
    return redirect(reverse('table_of_secification'))



@login_required(login_url='loginpage')
def table_of_specification_update(request, group_id):
    tos_entries = TableOfSpecification.objects.filter(group_id=group_id).select_related('subtopic', 'topic', 'subject')
    
    subject = tos_entries.first().subject.subject_name

    topics = {}
    overall_totals = {
        'remembering': 0,
        'understanding': 0,
        'applying': 0,
        'analyzing': 0,
        'evaluating': 0,
        'creating': 0,
    }

    for entry in tos_entries:
        entry.pwd = entry.pwd or 0
        for category in overall_totals.keys():
            count = getattr(entry, category)
            overall_totals[category] += count

            subtopic = entry.subtopic
            topic = entry.topic

            if topic.id not in topics:
                topics[topic.id] = {
                    'topic_name': topic.topic_name,
                    'totals': {cat: 0 for cat in overall_totals.keys()},
                    'subtopics': {}
                }

            topics[topic.id]['totals'][category] += count

            if subtopic.id not in topics[topic.id]['subtopics']:
                topics[topic.id]['subtopics'][subtopic.id] = {
                    'subtopic_id': subtopic.id,
                    'subtopic_name': subtopic.subtopic_name,
                    'totals': {cat: 0 for cat in overall_totals.keys()},
                    'pwd': entry.pwd, 
                }

            topics[topic.id]['subtopics'][subtopic.id]['totals'][category] += count

    overall_total = sum(overall_totals.values())

    context = {
        'group_id': group_id,
        'topics': topics.values(),
        'topic' : topics,
        'overall_totals': overall_totals,
        'overall_total': overall_total,
        'tos_entries': tos_entries,
        'subject' : subject,
    }

    return render(request, 'assets/masterfiletosupdate.html', context)




def submit_table_of_specification(request, group_id):
    if request.method == 'POST':
        entries = TableOfSpecification.objects.filter(group_id=group_id).select_related('subtopic')

        for entry in entries:
            subtopic_id = entry.subtopic_id
            try:
                entry.pwd = parse_decimal_input(
                    request.POST.get(f'pwd_{subtopic_id}', entry.pwd),
                    f"PWD for {entry.subtopic.subtopic_name}"
                )
                entry.remembering = parse_decimal_input(
                    request.POST.get(f'remembering_{subtopic_id}', entry.remembering),
                    f"Remembering for {entry.subtopic.subtopic_name}"
                )
                entry.understanding = parse_decimal_input(
                    request.POST.get(f'understanding_{subtopic_id}', entry.understanding),
                    f"Understanding for {entry.subtopic.subtopic_name}"
                )
                entry.applying = parse_decimal_input(
                    request.POST.get(f'applying_{subtopic_id}', entry.applying),
                    f"Applying for {entry.subtopic.subtopic_name}"
                )
                entry.analyzing = parse_decimal_input(
                    request.POST.get(f'analyzing_{subtopic_id}', entry.analyzing),
                    f"Analyzing for {entry.subtopic.subtopic_name}"
                )
                entry.evaluating = parse_decimal_input(
                    request.POST.get(f'evaluating_{subtopic_id}', entry.evaluating),
                    f"Evaluating for {entry.subtopic.subtopic_name}"
                )
                entry.creating = parse_decimal_input(
                    request.POST.get(f'creating_{subtopic_id}', entry.creating),
                    f"Creating for {entry.subtopic.subtopic_name}"
                )
            except ValidationError as exc:
                messages.error(request, exc.message)
                return redirect(reverse('table_of_specification_update', args=[group_id]))

            entry.save()

        messages.success(request, "Table of Specification updated successfully.")
        return redirect('table_of_secification')







def generate_unique_grouptos_id():
    while True:
        group_id = rd.randint(132414, 199999)
        if not TableOfSpecification.objects.filter(group_id=group_id).exists():
            return group_id


def generate_unique_row_tos_id():
    while True:
        row_id = rd.randint(132414, 199999)
        if not TableOfSpecification.objects.filter(row_id=row_id).exists():
            return row_id


@login_required(login_url='loginpage')
def table_of_secificationcreate(request, pk):
    subject = get_object_or_404(Subject, id=pk)
    topics = Topic.objects.filter(subject_topic=subject).prefetch_related('subtopic_set')

    if request.method == 'POST':
        group_id = generate_unique_grouptos_id()
        active_academic_year = AcademicYear.objects.filter(status=1).first()

        try:
            with transaction.atomic():
                for topic in topics:
                    for subtopic in topic.subtopic_set.all():
                        row_id = generate_unique_row_tos_id()
                        try:
                            sub_remembering = parse_decimal_input(
                                request.POST.get(f'subtopic_remembering_{subtopic.id}', 0),
                                f"Remembering for {subtopic.subtopic_name}"
                            )
                            sub_understanding = parse_decimal_input(
                                request.POST.get(f'subtopic_understanding_{subtopic.id}', 0),
                                f"Understanding for {subtopic.subtopic_name}"
                            )
                            sub_applying = parse_decimal_input(
                                request.POST.get(f'subtopic_applying_{subtopic.id}', 0),
                                f"Applying for {subtopic.subtopic_name}"
                            )
                            sub_analyzing = parse_decimal_input(
                                request.POST.get(f'subtopic_analyzing_{subtopic.id}', 0),
                                f"Analyzing for {subtopic.subtopic_name}"
                            )
                            sub_evaluating = parse_decimal_input(
                                request.POST.get(f'subtopic_evaluating_{subtopic.id}', 0),
                                f"Evaluating for {subtopic.subtopic_name}"
                            )
                            sub_creating = parse_decimal_input(
                                request.POST.get(f'subtopic_creating_{subtopic.id}', 0),
                                f"Creating for {subtopic.subtopic_name}"
                            )
                            sub_pwd = parse_decimal_input(
                                request.POST.get(f'subtopic_pwd_{subtopic.id}', 0),
                                f"PWD for {subtopic.subtopic_name}"
                            )
                        except ValidationError as exc:
                            raise ValidationError(exc.message)

                        TableOfSpecification.objects.create(
                            row_id=row_id,
                            pwd=sub_pwd,
                            academic_year=active_academic_year,
                            subject=subtopic.topic_subtopic.subject_topic,
                            topic=subtopic.topic_subtopic,
                            subtopic=subtopic,
                            group_id=group_id,
                            remembering=sub_remembering,
                            understanding=sub_understanding,
                            applying=sub_applying,
                            analyzing=sub_analyzing,
                            evaluating=sub_evaluating,
                            creating=sub_creating,
                        )

                        PercentageWeightPerTos.objects.create(
                            group_id=group_id,
                            row_id=row_id,
                            pwd=sub_pwd,
                        )
        except ValidationError as exc:
            messages.error(request, exc.message)
            context = {
                'subject': subject,
                'topics': topics,
            }
            return render(request, 'assets/masterfiletoscreate.html', context)

        messages.success(request, "Table of Specification created successfully!")
        return redirect('table_of_secification')

    context = {
        'subject': subject,
        'topics': topics,
    }

    return render(request, 'assets/masterfiletoscreate.html', context)


@login_required(login_url='loginpage')
def assessment(request):
    query = request.GET.get('q')
    active_academic_year = AcademicYear.objects.filter(status=1).first()

    if active_academic_year is None:
        representative_records = []
    else:
        if query:
            assessment = (
                Assessment.objects
                .filter(
                    Q(academic_year=active_academic_year) & 
                    (Q(assessment_id__icontains=query) |
                     Q(subject__subject_code__icontains=query) |
                     Q(topic__topic_name__icontains=query))
                )
                .values('assessment_id')
                .annotate(max_id=Max('id'))
            )
        else:
            assessment = (
                Assessment.objects
                .filter(academic_year=active_academic_year)
                .values('assessment_id')
                .annotate(max_id=Max('id'))
            )

        representative_records = Assessment.objects.filter(
            id__in=[entry['max_id'] for entry in assessment]
        ).annotate(
            percentage_weight=Subquery(
                PercentageWeightPerAssessment.objects
                .filter(assessment_id=OuterRef('assessment_id'))
                .values('percentage_w_assess')[:1]
            )
        ).order_by('-id')

    subjects = Subject.objects.all()
    context = {
        'subjects': subjects,
        'assessment': representative_records,
        'q': query
    }
    return render(request, 'assets/masterfileassessment.html', context)





def generate_unique_assessment_id():
    while True:
        assessment_id = rd.randint(132414, 199999)
        if not Assessment.objects.filter(assessment_id=assessment_id).exists():
            return assessment_id


@login_required(login_url='loginpage')
def assessment_create(request):
    subject = Subject.objects.all()
    assessment_datas = Assessment.objects.all().order_by('-id')
    topic_to_table = None
    subtopics = []

    if request.method == "POST":
        subject_id = request.POST.get('subjectdropdown_assessment')
        topic_id = request.POST.get('topicdropdown_assessment')
        percentage_w_assess_raw = request.POST.get('percentage_w_assessment')

        if not subject_id or not topic_id or percentage_w_assess_raw is None:
            messages.error(request, 'Please select Subject, Topic, and provide a Percentage Weight.')
            context = {
                'assessment': assessment_datas,
                'subject': subject,
                'topic': topic_to_table,
                'subtopics': subtopics,
            }
            return render(request, 'assets/masterfileassessment_create.html', context)

        try:
            subject_to_table = Subject.objects.get(id=subject_id)
            topic_to_table = Topic.objects.get(id=topic_id)
            subtopics = list(Subtopic.objects.filter(topic_subtopic=topic_to_table))
            active_academic_year = AcademicYear.objects.filter(status=1).first()
        except Subject.DoesNotExist:
            raise Http404("Subject not found.")
        except Topic.DoesNotExist:
            raise Http404("Topic not found.")

        try:
            percentage_w_assess = parse_decimal_input(percentage_w_assess_raw, "Percentage Weight")
        except ValidationError as exc:
            messages.error(request, exc.message)
            context = {
                'assessment': assessment_datas,
                'subject': subject,
                'topic': topic_to_table,
                'subtopics': subtopics,
            }
            return render(request, 'assets/masterfileassessment_create.html', context)

        assessment_id = generate_unique_assessment_id()

        try:
            with transaction.atomic():
                for subtopic in subtopics:
                    try:
                        remembering = parse_decimal_input(
                            request.POST.get(f'subtopic_remembering_{subtopic.id}', 0),
                            f"Remembering for {subtopic.subtopic_name}"
                        )
                        understanding = parse_decimal_input(
                            request.POST.get(f'subtopic_understanding_{subtopic.id}', 0),
                            f"Understanding for {subtopic.subtopic_name}"
                        )
                        applying = parse_decimal_input(
                            request.POST.get(f'subtopic_applying_{subtopic.id}', 0),
                            f"Applying for {subtopic.subtopic_name}"
                        )
                        analyzing = parse_decimal_input(
                            request.POST.get(f'subtopic_analyzing_{subtopic.id}', 0),
                            f"Analyzing for {subtopic.subtopic_name}"
                        )
                        evaluating = parse_decimal_input(
                            request.POST.get(f'subtopic_evaluating_{subtopic.id}', 0),
                            f"Evaluating for {subtopic.subtopic_name}"
                        )
                        creating = parse_decimal_input(
                            request.POST.get(f'subtopic_creating_{subtopic.id}', 0),
                            f"Creating for {subtopic.subtopic_name}"
                        )
                    except ValidationError as exc:
                        raise ValidationError(exc.message)

                    Assessment.objects.create(
                        academic_year=active_academic_year,
                        assessment_id=assessment_id,
                        subject=subject_to_table,
                        topic=topic_to_table,
                        competencies=subtopic,
                        remembering=remembering,
                        understanding=understanding,
                        applying=applying,
                        analyzing=analyzing,
                        evaluating=evaluating,
                        creating=creating,
                    )

                PercentageWeightPerAssessment.objects.create(
                    assessment_id=assessment_id,
                    percentage_w_assess=percentage_w_assess,
                )
        except ValidationError as exc:
            messages.error(request, exc.message)
            context = {
                'assessment': assessment_datas,
                'subject': subject,
                'topic': topic_to_table,
                'subtopics': subtopics,
            }
            return render(request, 'assets/masterfileassessment_create.html', context)

        messages.success(request, 'Created successfully!')
        return redirect('assessment')

    context = {
        'assessment': assessment_datas,
        'subject': subject,
        'topic': topic_to_table,
        'subtopics': subtopics,
    }

    return render(request, 'assets/masterfileassessment_create.html', context)


@login_required(login_url='loginpage')
def assessment_update(request, assessment_id):
    assessments_to_update = Assessment.objects.filter(assessment_id=assessment_id)
    percentage = PercentageWeightPerAssessment.objects.filter(assessment_id=assessment_id).first()

    if not assessments_to_update:
        messages.error(request, "No assessments found for the given ID.")
        return redirect(reverse('assessment'))

    if not percentage:
        messages.error(request, "Percentage weight not found for the given assessment ID.")
        return redirect(reverse('assessment'))

    if request.method == 'POST':
        per = request.POST.get('percentage_w_assessment_update')
        if per:
            try:
                percentage.percentage_w_assess = parse_decimal_input(per, "Percentage weight")
                percentage.save()
            except ValidationError as exc:
                messages.error(request, exc.message)
                return redirect(request.path)

        try:
            for assessment in assessments_to_update:
                remembering = request.POST.get(f'remembering_{assessment.id}')
                understanding = request.POST.get(f'understanding_{assessment.id}')
                applying = request.POST.get(f'applying_{assessment.id}')
                analyzing = request.POST.get(f'analyzing_{assessment.id}')
                evaluating = request.POST.get(f'evaluating_{assessment.id}')
                creating = request.POST.get(f'creating_{assessment.id}')

                if not all([remembering, understanding, applying, analyzing, evaluating, creating]):
                    messages.error(request, f"All fields must be filled out for assessment {assessment.id}.")
                    return redirect(request.path)

                try:
                    values = [
                        parse_decimal_input(remembering, "Remembering"),
                        parse_decimal_input(understanding, "Understanding"),
                        parse_decimal_input(applying, "Applying"),
                        parse_decimal_input(analyzing, "Analyzing"),
                        parse_decimal_input(evaluating, "Evaluating"),
                        parse_decimal_input(creating, "Creating"),
                    ]
                except ValidationError as exc:
                    messages.error(request, exc.message)
                    return redirect(request.path)

                if any(val < 0 for val in values):
                    messages.error(request, "All values must be non-negative.")
                    return redirect(request.path)

                (
                    assessment.remembering,
                    assessment.understanding,
                    assessment.applying,
                    assessment.analyzing,
                    assessment.evaluating,
                    assessment.creating,
                ) = values
                assessment.save()

            messages.success(request, f'Updated successfully!')
            return redirect(reverse('assessment'))

        except ValidationError as exc:
            messages.error(request, exc.message)
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    subjects = Subject.objects.all()

    context = {
        "assessments_to_update": assessments_to_update,
        "subjects": subjects,
        "percentage": percentage,
    }

    return render(request, 'assets/masterfileassessment_update.html', context)


def assessment_delete(request, assessment_id):
    Assessment.objects.filter(assessment_id=assessment_id).delete()

    PercentageWeightPerAssessment.objects.filter(assessment_id=assessment_id).delete()

    return redirect(reverse('assessment'))




@login_required(login_url='loginpage')
def masterfilestudents(request):
    query = request.GET.get('q')
    active_academic_year = AcademicYear.objects.filter(status=1).first()

    if active_academic_year is None:
        if query:
            students = Students.objects.filter(
                Q(lastname__icontains=query) |
                Q(firstname__icontains=query) |
                Q(studentid__icontains=query)
            ).order_by('-id')
        else:
            students = Students.objects.all().order_by('-id')
    else:
        if query:
            students = Students.objects.filter(
                Q(academic_year=active_academic_year) &
                (Q(lastname__icontains=query) |
                 Q(firstname__icontains=query) |
                 Q(studentid__icontains=query))
            ).order_by('-id')
        else:
            students = Students.objects.filter(academic_year=active_academic_year).order_by('-id')
    
    context = {'students': students, 'q': query}
    return render(request, 'assets/masterfilestudents.html', context)


@login_required(login_url='loginpage')
def process_csv_data(request):
    active_academic_year = AcademicYear.objects.filter(status=1).first()
    if request.method == 'POST':
        firstname_index = int(request.POST['firstname'])
        lastname_index = int(request.POST['lastname'])
        student_id_index = int(request.POST['student_id'])

        csv_file_data = request.session.get('csv_file_data')
        csv_reader = csv.reader(StringIO(csv_file_data))

        next(csv_reader)

        existing_students = []

        for row in csv_reader:
            studentschoolid = row[student_id_index]
            if Students.objects.filter(studentschoolid=studentschoolid).exists():
                existing_student = Students.objects.filter(studentschoolid=studentschoolid).first()
                existing_students.append(f"{existing_student.firstname} {existing_student.lastname}")
            else:
                Students.objects.create(
                    firstname=row[firstname_index],
                    lastname=row[lastname_index],
                    studentschoolid=studentschoolid,
                    academic_year=active_academic_year,
                    studentid=generate_unique_student_id(),
                )

        if existing_students:
            existing_students_str = ', '.join(existing_students)
            return render(request, 'assets/masterfilestudents_import.html', {
                'message': f'CSV data successfully saved! However, the following students already have existing Student IDs and were not registered again: {existing_students_str}'
            })
        else:
            return render(request, 'assets/masterfilestudents_import.html', {
                'message': 'CSV data successfully saved!'
            })
    return render(request, 'assets/masterfilestudents_import.html')




@login_required(login_url='loginpage')
def upload_csv(request):
    data = []
    if request.method == 'POST' and request.FILES['csv_file']:
        csv_file = request.FILES['csv_file']
        csv_file_data = csv_file.read().decode('utf-8')
        csv_reader = csv.reader(StringIO(csv_file_data))

        for row in csv_reader:
            data.append(row)


        request.session['csv_file_data'] = csv_file_data

        return render(request, 'assets/masterfilestudents_import.html', {
            'data': data
        })
    return render(request, 'assets/masterfilestudents_import.html')



def export_students(request):
    active_academic_year = AcademicYear.objects.filter(status=1).first()

    if active_academic_year:
        students = Students.objects.filter(academic_year=active_academic_year)
    else:
        students = []

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Last Name', 'First Name', 'Academic Period'])

    for student in students:
        if student.academic_year:
            academic_year = f"{student.academic_year.year_series} - {student.academic_year.period}"
        else:
            academic_year = "N/A"

        writer.writerow([student.studentid, student.lastname, student.firstname, academic_year])

    return response



def generate_unique_student_id():
    while True:
        student_id = rd.randint(132414, 199999)
        if not Students.objects.filter(studentid=student_id).exists():
            return student_id


@login_required(login_url='loginpage')
def masterfilestudentscreate(request):
    academicyear = AcademicYear.objects.filter(status=1)
    studentid = generate_unique_student_id()

    if request.method == 'POST':
        lastname = request.POST.get('lastName')
        firstname = request.POST.get('firstName')
        acadyear_id = request.POST.get('acadyear')
        schoolid = request.POST.get('studentschoolid')
        acadsyear = get_object_or_404(AcademicYear, pk=acadyear_id)

        datas = Students.objects.create(
            lastname=lastname,
            firstname=firstname,
            studentid=studentid,
            academic_year=acadsyear,
            studentschoolid=schoolid,
        )
        datas.save()
        messages.success(request, 'Student Added!')
        return redirect(reverse('masterfilestudents'))

    context = {'academicyear': academicyear, 'studentid': studentid}
    return render(request, 'assets/masterfilestudentscreate.html', context)



@login_required(login_url='loginpage')
def masterfilestudentsupdate(request, pk):

    student = get_object_or_404(Students, id=pk)

    context = {'student': student}
    if request.method == 'POST':
        try :
            lastname = request.POST.get('lastName_update')
            firstname = request.POST.get('firstName_update')

            students = get_object_or_404(Students, id=pk)

            students.lastname = lastname
            students.firstname = firstname

            students.save()
            messages.success(request, 'Student updated successfully!')
            return redirect(reverse('masterfilestudents'))
        except :
            pass
    return render(request, 'assets/masterfilestudentsupdate.html', context)

def student_cancel_update(request):

    
    return redirect('masterfilestudents')


def deletestudent(request, id):
    q = get_object_or_404(Students, id=id)
    q.delete()
    return redirect(reverse('masterfilestudents'))


# ==============OMR EXAM CHECKER===============

@login_required(login_url='loginpage')
def check_tos(request):
    query = request.GET.get('q', '')
    active_academic_year = AcademicYear.objects.filter(status=1).first()

    representatives = AnswerKeyTableOfSpecification.objects.filter(academic_year=active_academic_year).values('tos_exam_id').distinct()

    representative_entries = []
    for tos_exam in representatives:
        if query:
            representative = AnswerKeyTableOfSpecification.objects.filter(
                Q(academic_year=active_academic_year) &
                Q(tos_exam_id=tos_exam['tos_exam_id']) &
                Q(tos_exam_id__icontains=query)
            ).first()
        else:
            representative = AnswerKeyTableOfSpecification.objects.filter(
                Q(academic_year=active_academic_year) &
                Q(tos_exam_id=tos_exam['tos_exam_id'])
            ).first()
        
        if representative:
            representative_entries.append(representative)

    context = {
        'representative_entries': representative_entries,
        'q': query
    }
    return render(request, "assets/examchecker_tos_check_lists.html", context)



@login_required(login_url='loginpage')
def check_assessment(request):
    query = request.GET.get('q', '')
    active_academic_year = AcademicYear.objects.filter(status=1).first()
    
    representatives = AnswerKeyAssessment.objects.filter(academic_year=active_academic_year).values('assessment_exam_id').distinct()

    representative_entries = []
    for assessment_exam in representatives:
        if query:
            representative = AnswerKeyAssessment.objects.filter(
                Q(academic_year=active_academic_year) &
                Q(assessment_exam_id=assessment_exam['assessment_exam_id']) &
                Q(assessment_exam_id__icontains=query)
            ).first()
        else:
            representative = AnswerKeyAssessment.objects.filter(
                Q(academic_year=active_academic_year) &
                Q(assessment_exam_id=assessment_exam['assessment_exam_id'])
            ).first()
        
        if representative: 
            representative_entries.append(representative)

    context = {
        'representative_entries': representative_entries,
        'q': query
    }
    return render(request, "assets/examchecker_assessment_check_lists.html", context)



def get_representative_exam_ids():
    exam_ids = AnswerKeyTableOfSpecification.objects.values('tos_exam_id').distinct()

    representative_exam_ids = {}
    for exam_id in exam_ids:
        tos_exam_id = exam_id['tos_exam_id']
        representative_exam_id = AnswerKeyTableOfSpecification.objects.filter(tos_exam_id=tos_exam_id).first()
        if representative_exam_id:
            representative_exam_ids[tos_exam_id] = representative_exam_id

    return representative_exam_ids


@login_required(login_url='loginpage')
def import_csv_tos(request, tos_exam_id):
    active_year = AcademicYear.objects.get(status=1)
    exam_id = AnswerKeyTableOfSpecification.objects.filter(tos_exam_id=tos_exam_id).values('tos_exam_id').distinct()
    
    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]
        exam_tos_id = request.POST.get('exam_tos_id')  
        request.session['exam_tos_id'] = exam_tos_id
        
        try:
            data = pd.read_csv(csv_file)
            required_columns = ['ZipGrade ID', 'First Name', 'External Id', 'Last Name', 'Class', 'Num Correct', 'Num Questions']
            question_columns = [col for col in data.columns if col.startswith('Q') and col[1:].isdigit()]
            all_columns = required_columns + question_columns

            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                return render(request, "assets/examchecker_tos.html", {
                    "error": f"Missing columns: {', '.join(missing_columns)}",
                    'exam_id': exam_id,
                    'selected_exam_tos_id': exam_tos_id
                })

            data = data.dropna()
            students = Students.objects.all().values('studentid', 'firstname', 'lastname')
            students_df = pd.DataFrame.from_records(students)
            merged_data = pd.merge(data, students_df, left_on='External Id', right_on='studentid')

            question_mapping = {col: int(col[1:]) for col in question_columns}
            for key, value in question_mapping.items():
                merged_data[key] = merged_data[key].apply(lambda x: 1 if x == 1 else 0)

            total_students = len(merged_data)
            passing_threshold = 0.75 * total_students
            restricted_questions = []
            restricted_count_by_category = {category: 0 for category in ['understanding', 'remembering', 'creating', 'evaluating', 'analyzing', 'applying']}

            for question, question_number in question_mapping.items():
                correct_count = merged_data[question].sum()
                if correct_count >= passing_threshold:
                    answer_key_entry = AnswerKeyTableOfSpecification.objects.get(number=question_number, tos_exam_id=tos_exam_id)
                    question_description = answer_key_entry.question.id
                    restricted_questions.append(question_description)

                    if answer_key_entry.category in restricted_count_by_category:
                        restricted_count_by_category[answer_key_entry.category] += 1

            merged_data['Total Score'] = merged_data[question_columns].sum(axis=1)
            merged_data['Rank'] = merged_data['Total Score'].rank(method='dense', ascending=False).astype(int)
            sorted_data = merged_data.sort_values(by='Rank')

            html_table = sorted_data[['Rank', 'First Name', 'Last Name', 'Class', 'Total Score']].to_html(
                classes="table-auto border-collapse border border-gray-400 w-full text-sm text-left", index=False
            ).replace('<td>', '<td class="text-left px-4">').replace('<th>', '<th class="text-left px-4">')

            request.session['sorted_data'] = sorted_data.to_dict('records')
            request.session['restricted_questions'] = restricted_questions
            request.session['restricted_count_by_category'] = restricted_count_by_category
            request.session['tos_exam_id'] = tos_exam_id 
            
            restricted_questions_to_show = Questionnaire.objects.filter(id__in=restricted_questions)

            student_topic_subtopic_counts = {}

            for index, row in merged_data.iterrows():
                student_id = row['External Id']
                student_name = f"{row['firstname']} {row['lastname']}"
                for col, number in question_mapping.items():
                    tos_entry = AnswerKeyTableOfSpecification.objects.get(tos_exam_id=tos_exam_id, number=number)
                    topic_name = tos_entry.topic.topic_name
                    subtopic_name = tos_entry.subtopic.subtopic_name
                    if student_name not in student_topic_subtopic_counts:
                        student_topic_subtopic_counts[student_name] = {}
                    if topic_name not in student_topic_subtopic_counts[student_name]:
                        student_topic_subtopic_counts[student_name][topic_name] = {}
                    if subtopic_name not in student_topic_subtopic_counts[student_name][topic_name]:
                        student_topic_subtopic_counts[student_name][topic_name][subtopic_name] = {'question_count': 0, 'correct_count': 0}
                    student_topic_subtopic_counts[student_name][topic_name][subtopic_name]['question_count'] += 1
                    if row[col] == 1:  
                        student_topic_subtopic_counts[student_name][topic_name][subtopic_name]['correct_count'] += 1

            for student_name in merged_data.apply(lambda x: f"{x['firstname']} {x['lastname']}", axis=1).unique():
                if student_name not in student_topic_subtopic_counts:
                    student_topic_subtopic_counts[student_name] = {}

            context = {
                'tos_exam_id' : tos_exam_id,
                'exam_id': exam_id,
                'scores_table': html_table, 
                'restricted_questions': restricted_questions_to_show, 
                'restricted_count_by_category': restricted_count_by_category,
                'selected_exam_tos_id': exam_tos_id,
                'exam_ids': get_representative_exam_ids(),
                'student_topic_subtopic_counts': student_topic_subtopic_counts,
                'sorted_data': sorted_data.to_dict('records'), 
            }

            return render(request, "assets/examchecker_tos.html", context)

        except Exception as e:
            return render(request, "assets/examchecker_tos.html", {
                'tos_exam_id' : tos_exam_id,
                "error": f"An error occurred: {e}",
                'exam_id': exam_id,
                'selected_exam_tos_id': exam_tos_id,
                'exam_ids': get_representative_exam_ids()
            })
    
    selected_exam_tos_id = request.session.get('exam_tos_id', '')  
    
    return render(request, "assets/examchecker_tos.html", {
        'tos_exam_id' : tos_exam_id,
        'exam_id': exam_id,
        'selected_exam_tos_id': selected_exam_tos_id,
        'exam_ids': get_representative_exam_ids()
    })




def save_data_tos(request):
    if request.method == "POST":
        active_year = AcademicYear.objects.get(status=1)
        sorted_data = request.session.get('sorted_data', [])
        # restricted_questions = request.session.get('restricted_questions', [])
        tos_exam_id = request.session.get('tos_exam_id')
        
        # for description in restricted_questions:
        #     Questionnaire.objects.filter(id=description).update(status=1)

        StudentStatsTos.objects.filter(tos_exam__tos_exam_id=tos_exam_id).delete()

        tos_checked_list = AnswerKeyTableOfSpecification.objects.filter(tos_exam_id=tos_exam_id)

        for item in tos_checked_list:
            item.status = 1
            item.save()

        categories = ['understanding', 'remembering', 'creating', 'evaluating', 'analyzing', 'applying']
        category_count = {category: 0 for category in categories}
        correct_count = {f"{category}_correct_total": 0 for category in categories}
        subject_count = {}
        subject_correct_count = {}

        aggregated_stats = {}

        for row in sorted_data:
            student = Students.objects.get(studentid=row['studentid'])
            
            studentscore, created = StudentsScoreTos.objects.update_or_create(
                studentid=student.studentid, 
                academic_year=active_year,
                defaults={
                    'score': row['Total Score'],
                    'rank': row['Rank'],
                    'lastname': row['Last Name'],
                    'firstname': row['First Name'],
                    'period': row['Class'],
                    'exam_id': tos_exam_id,
                }
            )

            question_mapping = {col: int(col[1:]) for col in row.keys() if col.startswith('Q') and col[1:].isdigit()}

            for key, value in question_mapping.items():
                tos = AnswerKeyTableOfSpecification.objects.filter(number=value, tos_exam_id=tos_exam_id).first()
                
                if tos:
                    topic_name = tos.topic.topic_name 
                    subtopic_name = tos.subtopic.subtopic_name 
                    topic, _ = Topic.objects.get_or_create(topic_name=topic_name)
                    subtopic, _ = Subtopic.objects.get_or_create(subtopic_name=subtopic_name, topic_subtopic=topic)
                    
                    if (student.studentid, subtopic.id, tos.row_id) not in aggregated_stats:
                        aggregated_stats[(student.studentid, subtopic.id, tos.row_id)] = {
                            'student': student,
                            'subtopic': subtopic,
                            'tos_exam': tos,
                            'question_count': 0,
                            'correct_count': 0
                        }
                    aggregated_stats[(student.studentid, subtopic.id, tos.row_id)]['question_count'] += 1
                    if row[key] == 1:
                        aggregated_stats[(student.studentid, subtopic.id, tos.row_id)]['correct_count'] += 1

            studentscore.save()

        for (studentid, subtopic_id, row_id), stats in aggregated_stats.items():
            StudentStatsTos.objects.create(
                student=stats['student'],
                subtopic=stats['subtopic'],
                tos_exam=stats['tos_exam'],
                question_count=stats['question_count'],
                correct_count=stats['correct_count'],
                row_id=row_id
            )

        for subject_id, total_questions in subject_count.items():
            total_correct = subject_correct_count.get(subject_id, 0)

            existing_subject = SubjectCountPercentage.objects.filter(
                academic_year=active_year, subject_id=subject_id
            ).first()

            if existing_subject:
                existing_subject.total_q_counts_per_subject += total_questions
                existing_subject.total_correct_counts_per_subject += total_correct
                existing_subject.save()
            else:
                SubjectCountPercentage.objects.create(
                    academic_year=active_year,
                    subject_id=subject_id,
                    total_q_counts_per_subject=total_questions,
                    total_correct_counts_per_subject=total_correct,
                )

        total_questions = sum(category_count.values())
        if total_questions == 0:
            total_questions = 1 

        existing_category = CategoriesCountPercentage.objects.filter(academic_year=active_year).first()

        if existing_category:
            existing_category.remembering += category_count.get('remembering', 0)
            existing_category.creating += category_count.get('creating', 0)
            existing_category.understanding += category_count.get('understanding', 0)
            existing_category.applying += category_count.get('applying', 0)
            existing_category.analyzing += category_count.get('analyzing', 0)
            existing_category.evaluating += category_count.get('evaluating', 0)

            existing_category.remembering_correct_total += correct_count.get('remembering_correct_total', 0)
            existing_category.creating_correct_total += correct_count.get('creating_correct_total', 0)
            existing_category.understanding_correct_total += correct_count.get('understanding_correct_total', 0)
            existing_category.applying_correct_total += correct_count.get('applying_correct_total', 0)
            existing_category.analyzing_correct_total += correct_count.get('analyzing_correct_total', 0)
            existing_category.evaluating_correct_total += correct_count.get('evaluating_correct_total', 0)

            existing_category.save()
        else:
            CategoriesCountPercentage.objects.create(
                academic_year=active_year,
                remembering=category_count.get('remembering', 0),
                creating=category_count.get('creating', 0),
                understanding=category_count.get('understanding', 0),
                applying=category_count.get('applying', 0),
                analyzing=category_count.get('analyzing', 0),
                evaluating=category_count.get('evaluating', 0),
                remembering_correct_total=correct_count.get('remembering_correct_total', 0),
                creating_correct_total=correct_count.get('creating_correct_total', 0),
                understanding_correct_total=correct_count.get('understanding_correct_total', 0),
                applying_correct_total=correct_count.get('applying_correct_total', 0),
                analyzing_correct_total=correct_count.get('analyzing_correct_total', 0),
                evaluating_correct_total=correct_count.get('evaluating_correct_total', 0),
            )

        del request.session['sorted_data']
        del request.session['restricted_questions']
        del request.session['tos_exam_id']

        return redirect('check_tos')






def get_assessment_details(assessment_id):
    try:
        assessment = Assessment.objects.select_related('subject', 'topic').filter(assessment_id=assessment_id).first()
        if not assessment:
            return None, None, None

        topic_name = assessment.topic.topic_name if assessment.topic else "N/A"
        subject_name = assessment.subject.subject_code if assessment.subject else "N/A"
        percentage_weight = PercentageWeightPerAssessment.objects.filter(assessment_id=assessment_id).values_list('percentage_w_assess', flat=True).first()

        with transaction.atomic():
            report = Reports(
                assessment_id=assessment_id,
                percentage_weight=percentage_weight,
                subject = subject_name,
                topic = topic_name,
                created_at=timezone.now()
            )
            report.save()

        return topic_name, subject_name, percentage_weight
    except Exception as e:
        print(f"Error saving report: {e}")
        return None, None, None


def save_top_5_students(assessment_exam_id, top_5_students):

    for student in top_5_students:
        StudentsTop5.objects.create(
            assessment_id=assessment_exam_id,
            first_name=student['First Name'],
            lastname=student['Last Name'],
            score=student['Total Score'],
            rank=student['Rank']
        )



def save_high_accuracy_questions(assessment_id, high_accuracy_questions):
    with transaction.atomic():
        for question in high_accuracy_questions:
            try:
                q_key = question['description']
                question_description = Questionnaire.objects.get(id=q_key).description

                HighPQuestionsReports.objects.create(
                    assessment_id=assessment_id,
                    high_p_q=question_description,
                    number=question['question_number'],
                    percentage=question['percentage']
                )
            except Questionnaire.DoesNotExist:
                print(f"Question with ID {q_key} does not exist.")


def save_low_accuracy_questions(assessment_id, low_accuracy_questions):
    with transaction.atomic():
        for question in low_accuracy_questions:
            try:
                q_key = question['description']
                question_description = Questionnaire.objects.get(id=q_key).description

                LowPQuestionsReports.objects.create(
                    assessment_id=assessment_id,
                    low_p_q=question_description,
                    number=question['question_number'],
                    percentage=question['percentage']
                )
            except Questionnaire.DoesNotExist:
                print(f"Question with ID {q_key} does not exist.")


def save_restricted_counts(assessment_id, restricted_count_by_category):
    with transaction.atomic():
        TableRestrictCountsPerCategoryReports.objects.create(
            assessment_id=assessment_id,
            remembering=restricted_count_by_category['remembering'],
            creating=restricted_count_by_category['creating'],
            understanding=restricted_count_by_category['understanding'],
            applying=restricted_count_by_category['applying'],
            analyzing=restricted_count_by_category['analyzing'],
            evaluating=restricted_count_by_category['evaluating']
        )


import numpy as np
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

@transaction.atomic
def save_correct_and_wrong_counts(correct_and_wrong_counts_data):
    for data in correct_and_wrong_counts_data:
        try:
            CorrectAndWrongCountsPerItem.objects.create(
                assessment_id=int(data['assessment_id']) if data['assessment_id'] is not None else None,
                number=int(data['number']),
                question_description=data['question_description'],
                correct_counts=int(data['correct_counts']),
                wrong_counts=int(data['wrong_counts'])
            )
        except Exception as e:
            logger.error(f"Error saving data: {data} with error: {e}")
            raise

@login_required(login_url='loginpage')
def import_csv_assessment(request, assessment_exam_id):
    active_year = AcademicYear.objects.get(status=1)
    exam_id = AnswerKeyAssessment.objects.filter(assessment_exam_id=assessment_exam_id).values('assessment_exam_id').distinct()

    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]
        exam_assessment_id = request.POST.get('exam_assessment_id')
        request.session['exam_assessment_id'] = exam_assessment_id

        try:
            data = pd.read_csv(csv_file)
            data = data.dropna()

            # Convert all int64 columns to int
            for col in data.select_dtypes(include=['int64']).columns:
                data[col] = data[col].astype(int)

            required_columns = ['ZipGrade ID', 'First Name', 'External Id', 'Last Name', 'Class', 'Num Correct', 'Num Questions']
            question_columns = [col for col in data.columns if col.startswith('Q') and col[1:].isdigit()]
            all_columns = required_columns + question_columns

            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                return render(request, "assets/examchecker_assessment.html", {
                    "error": f"Missing columns: {', '.join(missing_columns)}",
                    'exam_id': exam_id,
                    'selected_exam_assessment_id': exam_assessment_id
                })

            students = Students.objects.all().values('studentid', 'firstname', 'lastname')
            students_df = pd.DataFrame.from_records(students)
            merged_data = pd.merge(data, students_df, left_on='External Id', right_on='studentid')

            question_mapping = {col: int(col[1:]) for col in question_columns}

            correct_and_wrong_counts_data = []

            for question, question_number in question_mapping.items():
                correct_count = merged_data[question].sum()
                wrong_count = len(merged_data) - correct_count

                answer_key_entry = AnswerKeyAssessment.objects.get(number=question_number, assessment_exam_id=assessment_exam_id)
                question_description = answer_key_entry.question.description

                correct_and_wrong_counts_data.append({
                    'assessment_id': int(assessment_exam_id),
                    'number': question_number,
                    'question_description': question_description,
                    'correct_counts': int(correct_count),
                    'wrong_counts': int(wrong_count)
                })

            high_accuracy_questions = []
            low_accuracy_questions = []
            for question, question_number in question_mapping.items():
                correct_count = merged_data[question].sum()
                accuracy = correct_count / len(merged_data)
                if accuracy >= 0.8:
                    answer_key_entry = AnswerKeyAssessment.objects.get(number=question_number, assessment_exam_id=assessment_exam_id)
                    question_description = answer_key_entry.question.id
                    high_accuracy_questions.append({
                        'question_number': question_number,
                        'description': question_description,
                        'percentage': accuracy * 100
                    })
                elif accuracy <= 0.2:
                    answer_key_entry = AnswerKeyAssessment.objects.get(number=question_number, assessment_exam_id=assessment_exam_id)
                    question_description = answer_key_entry.question.id
                    low_accuracy_questions.append({
                        'question_number': question_number,
                        'description': question_description,
                        'percentage': accuracy * 100
                    })

            restricted_questions = []
            restricted_count_by_category = {category: 0 for category in ['understanding', 'remembering', 'creating', 'evaluating', 'analyzing', 'applying']}

            for question, question_number in question_mapping.items():
                correct_count = merged_data[question].sum()
                if correct_count >= 0.75 * len(merged_data):
                    answer_key_entry = AnswerKeyAssessment.objects.get(number=question_number, assessment_exam_id=assessment_exam_id)
                    question_description = answer_key_entry.question.id
                    restricted_questions.append(question_description)

                    if answer_key_entry.category in restricted_count_by_category:
                        restricted_count_by_category[answer_key_entry.category] += 1

            merged_data['Total Score'] = merged_data[question_columns].sum(axis=1)
            merged_data['Rank'] = merged_data['Total Score'].rank(method='dense', ascending=False).astype(int)
            sorted_data = merged_data.sort_values(by='Rank')

            top_5_students = sorted_data.head(5)[['First Name', 'Last Name', 'Total Score', 'Rank']].to_dict('records')

            html_table = sorted_data[['Rank', 'First Name', 'Last Name', 'Class', 'Total Score']].to_html(
                classes="table-auto border-collapse border border-gray-400 w-full text-sm text-left", index=False
            ).replace('<td>', '<td class="text-left px-4">').replace('<th>', '<th class="text-left px-4">')

            # Convert DataFrame to JSON-serializable dicts
            request.session['sorted_data'] = sorted_data.applymap(lambda x: int(x) if isinstance(x, np.int64) else x).to_dict('records')
            request.session['correct_and_wrong_counts_data'] = correct_and_wrong_counts_data
            request.session['restricted_questions'] = restricted_questions
            request.session['restricted_count_by_category'] = restricted_count_by_category
            request.session['assessment_exam_id'] = assessment_exam_id
            request.session['top_5_students'] = top_5_students
            request.session['high_accuracy_questions'] = high_accuracy_questions
            request.session['low_accuracy_questions'] = low_accuracy_questions
            request.session['restricted_count_by_category'] = restricted_count_by_category

            restricted_questions_to_show = Questionnaire.objects.filter(id__in=restricted_questions)
            context = {
                'exam_id': exam_id,
                'scores_table': html_table,
                'restricted_questions': restricted_questions_to_show,
                'restricted_count_by_category': restricted_count_by_category,
                'selected_exam_assessment_id': exam_assessment_id,
                'exam_ids': get_representative_exam_ids(),
                'top_5_students': top_5_students,
                'high_accuracy_questions': high_accuracy_questions,
                'low_accuracy_questions': low_accuracy_questions 
            }

            return render(request, "assets/examchecker_assessment.html", context)

        except Exception as e:
            logger.error(f"Exception occurred: {e}")
            return render(request, "assets/examchecker_assessment.html", {
                "error": f"An error occurred: {e}",
                'exam_id': exam_id,
                'selected_exam_assessment_id': exam_assessment_id,
                'exam_ids': get_representative_exam_ids()
            })

    selected_exam_assessment_id = request.session.get('exam_assessment_id', '')
    return render(request, "assets/examchecker_assessment.html", {
        'exam_id': exam_id,
        'selected_exam_assessment_id': selected_exam_assessment_id,
        'exam_ids': get_representative_exam_ids()
    })






def update_student_final_percentage(student_id):
    assessments = StudentStatsAssessment.objects.filter(student_id=student_id)
    
    total_final_percentage = 0
    for assessment in assessments:
        assessment.calculate_final_assess_percentage()
        total_final_percentage += assessment.final_assess_percentage

    return total_final_percentage



def save_data_assessment(request):
    if request.method == "POST":
        active_year = AcademicYear.objects.get(status=1)

        exam_id = request.session.get('assessment_exam_id')
        sorted_data = request.session.get('sorted_data', [])
        restricted_questions = request.session.get('restricted_questions', [])
        top_5_students = request.session.get('top_5_students')
        high_accuracy_questions = request.session.get('high_accuracy_questions')
        low_accuracy_questions = request.session.get('low_accuracy_questions')
        restricted_count_by_category = request.session.get('restricted_count_by_category')
        correct_and_wrong_counts_data = request.session.get('correct_and_wrong_counts_data')


        topic_name = Assessment.objects.filter(assessment_id = exam_id).first()

        save_correct_and_wrong_counts(correct_and_wrong_counts_data)

        save_restricted_counts(exam_id, restricted_count_by_category)
        
        save_low_accuracy_questions(exam_id, low_accuracy_questions)

        save_high_accuracy_questions(exam_id, high_accuracy_questions)

        save_top_5_students(exam_id, top_5_students)

        get_assessment_details(exam_id)

        assess_checked_list = AnswerKeyAssessment.objects.filter(assessment_exam_id=exam_id)

        for item in assess_checked_list:
            item.status = 1
            item.save()

        with transaction.atomic():
            try:
                for question_id in restricted_questions:
                    Questionnaire.objects.filter(id=question_id).update(status=1)

                categories = ['understanding', 'remembering', 'creating', 'evaluating', 'analyzing', 'applying']
                category_count = {category: 0 for category in categories}
                correct_count = {f"{category}_correct_total": 0 for category in categories}

                subject_count = {}
                subject_correct_count = {}

                for row in sorted_data:
                    student_score = {
                        'academic_year': active_year,
                        'score': row['Total Score'],
                        'rank': row['Rank'],
                        'lastname': row['Last Name'],
                        'firstname': row['First Name'],
                        'studentid': row['studentid'],
                        'period': row['Class'],
                        'exam_id': exam_id
                    }


                    student_entry, created = StudentsScoreAssessment.objects.update_or_create(
                        studentid=row['studentid'], 
                        period=row['Class'],
                        exam_id=exam_id,
                        defaults=student_score
                    )


                    question_mapping = {col: int(col[1:]) for col in row.keys() if col.startswith('Q') and col[1:].isdigit()}
                    for key, value in question_mapping.items():
                        assessment = AnswerKeyAssessment.objects.filter(number=value, assessment_exam_id=exam_id).first()

                        if assessment:
                            if assessment.category in categories:
                                category_count[assessment.category] += 1
                                if pd.notna(row[key]) and row[key] == 1: 
                                    correct_count[f"{assessment.category}_correct_total"] += 1

                            if assessment.subject:
                                subject_id = assessment.subject.id
                                if subject_id not in subject_count:
                                    subject_count[subject_id] = 0
                                    subject_correct_count[subject_id] = 0
                                subject_count[subject_id] += 1
                                if pd.notna(row[key]) and row[key] == 1:
                                    subject_correct_count[subject_id] += 1

                                student_entry.subject = assessment
                                student_entry.save()

                for subject_id, total_questions in subject_count.items():
                    total_correct = subject_correct_count.get(subject_id, 0)

                    existing_subject = SubjectCountPercentage.objects.filter(
                        academic_year=active_year, subject_id=subject_id
                    ).first()

                    if existing_subject:
                        existing_subject.total_q_counts_per_subject += total_questions
                        existing_subject.total_correct_counts_per_subject += total_correct
                        existing_subject.save()
                    else:
                        SubjectCountPercentage.objects.create(
                            academic_year=active_year,
                            subject_id=subject_id,
                            total_q_counts_per_subject=total_questions,
                            total_correct_counts_per_subject=total_correct,
                        )

                total_questions = sum(category_count.values())
                if total_questions == 0:
                    total_questions = 1

                existing_category = CategoriesCountPercentage.objects.filter(academic_year=active_year).first()
                existing_category_assessment = AssessmentRecordsDashboard.objects.filter(assessment_id=exam_id).first()

                

                if existing_category_assessment:
                    existing_category_assessment.remembering += category_count.get('remembering', 0)
                    existing_category_assessment.creating += category_count.get('creating', 0)
                    existing_category_assessment.understanding += category_count.get('understanding', 0)
                    existing_category_assessment.applying += category_count.get('applying', 0)
                    existing_category_assessment.analyzing += category_count.get('analyzing', 0)
                    existing_category_assessment.evaluating += category_count.get('evaluating', 0)

                    existing_category_assessment.remembering_correct_total += correct_count.get('remembering_correct_total', 0)
                    existing_category_assessment.creating_correct_total += correct_count.get('creating_correct_total', 0)
                    existing_category_assessment.understanding_correct_total += correct_count.get('understanding_correct_total', 0)
                    existing_category_assessment.applying_correct_total += correct_count.get('applying_correct_total', 0)
                    existing_category_assessment.analyzing_correct_total += correct_count.get('analyzing_correct_total', 0)
                    existing_category_assessment.evaluating_correct_total += correct_count.get('evaluating_correct_total', 0)



                    existing_category_assessment.category_total += category_count.get('remembering', 0)
                    existing_category_assessment.category_total += category_count.get('creating', 0)
                    existing_category_assessment.category_total += category_count.get('understanding', 0)
                    existing_category_assessment.category_total += category_count.get('applying', 0)
                    existing_category_assessment.category_total += category_count.get('analyzing', 0)
                    existing_category_assessment.category_total += category_count.get('evaluating', 0)

                    existing_category_assessment.category_correct_total += correct_count.get('remembering_correct_total', 0)
                    existing_category_assessment.category_correct_total += correct_count.get('creating_correct_total', 0)
                    existing_category_assessment.category_correct_total += correct_count.get('understanding_correct_total', 0)
                    existing_category_assessment.category_correct_total += correct_count.get('applying_correct_total', 0)
                    existing_category_assessment.category_correct_total += correct_count.get('analyzing_correct_total', 0)
                    existing_category_assessment.category_correct_total += correct_count.get('evaluating_correct_total', 0)


                    existing_category_assessment.save()


                else:
                    AssessmentRecordsDashboard.objects.create(
                        academic_year=active_year,
                        assessment_id = exam_id,
                        topic = topic_name.topic.topic_name,
                        subject_code = topic_name.subject.subject_code,
                        remembering=category_count.get('remembering', 0),
                        creating=category_count.get('creating', 0),
                        understanding=category_count.get('understanding', 0),
                        applying=category_count.get('applying', 0),
                        analyzing=category_count.get('analyzing', 0),
                        evaluating=category_count.get('evaluating', 0),
                        remembering_correct_total=correct_count.get('remembering_correct_total', 0),
                        creating_correct_total=correct_count.get('creating_correct_total', 0),
                        understanding_correct_total=correct_count.get('understanding_correct_total', 0),
                        applying_correct_total=correct_count.get('applying_correct_total', 0),
                        analyzing_correct_total=correct_count.get('analyzing_correct_total', 0),
                        evaluating_correct_total=correct_count.get('evaluating_correct_total', 0),

                        category_total = category_count.get('remembering', 0) + 
                                        category_count.get('creating', 0) + 
                                        category_count.get('understanding', 0) + 
                                        category_count.get('applying', 0) + 
                                        category_count.get('analyzing', 0) + 
                                        category_count.get('evaluating', 0),


                        
                        category_correct_total = correct_count.get('remembering_correct_total', 0) + 
                                                 correct_count.get('creating_correct_total', 0) + 
                                                 correct_count.get('understanding_correct_total', 0) + 
                                                 correct_count.get('applying_correct_total', 0) +
                                                 correct_count.get('analyzing_correct_total', 0) + 
                                                 correct_count.get('evaluating_correct_total', 0),

                    )




                if existing_category:
                    existing_category.remembering += category_count.get('remembering', 0)
                    existing_category.creating += category_count.get('creating', 0)
                    existing_category.understanding += category_count.get('understanding', 0)
                    existing_category.applying += category_count.get('applying', 0)
                    existing_category.analyzing += category_count.get('analyzing', 0)
                    existing_category.evaluating += category_count.get('evaluating', 0)

                    existing_category.remembering_correct_total += correct_count.get('remembering_correct_total', 0)
                    existing_category.creating_correct_total += correct_count.get('creating_correct_total', 0)
                    existing_category.understanding_correct_total += correct_count.get('understanding_correct_total', 0)
                    existing_category.applying_correct_total += correct_count.get('applying_correct_total', 0)
                    existing_category.analyzing_correct_total += correct_count.get('analyzing_correct_total', 0)
                    existing_category.evaluating_correct_total += correct_count.get('evaluating_correct_total', 0)

                    existing_category.save()


                else:
                    CategoriesCountPercentage.objects.create(
                        academic_year=active_year,
                        remembering=category_count.get('remembering', 0),
                        creating=category_count.get('creating', 0),
                        understanding=category_count.get('understanding', 0),
                        applying=category_count.get('applying', 0),
                        analyzing=category_count.get('analyzing', 0),
                        evaluating=category_count.get('evaluating', 0),
                        remembering_correct_total=correct_count.get('remembering_correct_total', 0),
                        creating_correct_total=correct_count.get('creating_correct_total', 0),
                        understanding_correct_total=correct_count.get('understanding_correct_total', 0),
                        applying_correct_total=correct_count.get('applying_correct_total', 0),
                        analyzing_correct_total=correct_count.get('analyzing_correct_total', 0),
                        evaluating_correct_total=correct_count.get('evaluating_correct_total', 0),
                    )

                for row in sorted_data:
                    student_id = row['studentid']
                    total_questions = row.get('Num Questions', 0)
                    total_score = row.get('Total Score', 0)

                    student = Students.objects.filter(studentid=student_id).first()
                    if student:
                        assessment_count = StudentStatsAssessment.objects.filter(student=student).count() + 1
                        student_stats, created = StudentStatsAssessment.objects.update_or_create(
                            academic_year = active_year,
                            student=student,
                            exam_id=exam_id,
                            defaults={
                                'total_questions_taken': total_questions,
                                'total_questions_score': total_score,
                                'assessment_taken_count': assessment_count
                            }
                        )
                        final_percentage = update_student_final_percentage(student_id)
                        print(f"Final Assessment Percentage for student {student_id}: {final_percentage}%")
                    else:
                        print(f"Student {student_id} does not exist in the Students table.")

                del request.session['sorted_data']
                del request.session['restricted_questions']
                del request.session['assessment_exam_id']
                del request.session['top_5_students']
                del request.session['high_accuracy_questions']
                del request.session['correct_and_wrong_counts_data']

                return redirect('check_assessment')

            except IntegrityError as e:
                print(f"IntegrityError: {e}")
                return render(request, "assets/examchecker_assessment.html", {
                    "error": f"An error occurred while saving: {e}",
                    'exam_id': exam_id,
                })
            except Exception as e:
                print(f"Unexpected error: {e}")
                return render(request, "assets/examchecker_assessment.html", {
                    "error": f"An unexpected error occurred: {e}",
                    'exam_id': exam_id,
                })




def get_unique_assessments_students_score():
    active_academic_year = AcademicYear.objects.filter(status=1).first()

    distinct_exam_ids = StudentsScoreAssessment.objects.filter(
        academic_year=active_academic_year
    ).values('exam_id').distinct()

    assessments = []
    for exam in distinct_exam_ids:
        representative_row = StudentsScoreAssessment.objects.filter(
            exam_id=exam['exam_id'], academic_year=active_academic_year
        ).first()

        if representative_row:
            assessments.append(representative_row)

    return assessments




def get_unique_table_of_specifications_students_score():
    active_academic_year = AcademicYear.objects.filter(status=1).first()
    
    table_of_specifications = StudentsScoreTos.objects.filter(academic_year=active_academic_year).order_by('exam_id')
    unique_tos = {}
    for tos in table_of_specifications:
        if tos.exam_id not in unique_tos:
            answer_key_tos = AnswerKeyTableOfSpecification.objects.filter(tos_exam_id=tos.exam_id).first()
            unique_tos[tos.exam_id] = {
                'exam_id': tos.exam_id,
                'subject_name': answer_key_tos.subject.subject_name if answer_key_tos else None,
            }
    return list(unique_tos.values())

@login_required(login_url='loginpage')
def rankings_scores(request):
    assessment = get_unique_assessments_students_score()
    table_of_specification = get_unique_table_of_specifications_students_score()

    context = {
        'assessment': assessment,
        'table_of_specification': table_of_specification,
    }

    return render(request, 'assets/examchecker_students_ranking.html', context)





@login_required(login_url='loginpage')
def students_stats(request):
    active_academic_year = AcademicYear.objects.filter(status=1).first()
    stud_stats = []
    student_info = []
    seen_students = set()

    if active_academic_year:
        max_assessment_count = StudentStatsAssessment.objects.filter(academic_year=active_academic_year).aggregate(Max('assessment_taken_count'))['assessment_taken_count__max']
        
        stud_stats = StudentStatsAssessment.objects.filter(
            academic_year=active_academic_year,
            assessment_taken_count=max_assessment_count
        )

        stud_stats = sorted(stud_stats, key=lambda x: x.score_percentage, reverse=True)
    
        student_stats_tos = StudentStatsTos.objects.filter(student__academic_year=active_academic_year)
        
        for stat in student_stats_tos:
            if stat.student.studentid not in seen_students:
                student_info.append({
                    'studentid': stat.student.studentid,
                    'firstname': stat.student.firstname,
                    'lastname': stat.student.lastname,
                    'passing_rate': stat.passing_rate  
                })
                seen_students.add(stat.student.studentid)

        student_info = sorted(student_info, key=lambda x: x['passing_rate'], reverse=True)

    context = {
        "stud_stats": stud_stats,
        "student_info": student_info
    }

    return render(request, 'assets/examchecker_students_stats.html', context)





@login_required(login_url='loginpage')
def students_all_stats_assessment(request, studentid):
    try:
        student = Students.objects.get(studentid=studentid)
        studentschoolid = Students.objects.filter(studentid=studentid).first()

        stud_stats = StudentStatsAssessment.objects.filter(student=student)

        assessments = Assessment.objects.select_related('topic', 'subject').filter(
            assessment_id__in=[stat.exam_id for stat in stud_stats]
        )

        exam_to_topic = {assessment.assessment_id: assessment.topic.topic_name for assessment in assessments}
        exam_to_subject_code = {assessment.assessment_id: assessment.subject.subject_code for assessment in assessments}

        exam_to_percentage = {}
        for stat in stud_stats:
            pwa = PercentageWeightPerAssessment.objects.filter(assessment_id=stat.exam_id, status=0).first()
            if pwa and pwa.percentage_w_assess is not None:
                exam_to_percentage[stat.exam_id] = float(pwa.percentage_w_assess)
            else:
                exam_to_percentage[stat.exam_id] = None

        full_name = f"{student.firstname} {student.lastname}"

        assessment_count = [stat.assessment_taken_count_calculated for stat in stud_stats]
        assessment_counts = assessment_count[0] if assessment_count else []

        score_percentage = [stat.score_percentage for stat in stud_stats]
        score_percentages = score_percentage[0] if score_percentage else []

        subject_totals = {}
        for stat in stud_stats:
            subject_code = exam_to_subject_code.get(stat.exam_id)
            if subject_code not in subject_totals:
                subject_totals[subject_code] = {
                    'total_contribution': 0,
                    'total_percentage_w_assess': 0,
                }

            subject_totals[subject_code]['total_contribution'] += stat.contribution or 0
            percentage_value = exam_to_percentage.get(stat.exam_id) or 0.0
            subject_totals[subject_code]['total_percentage_w_assess'] += percentage_value

            stat.topic_name = exam_to_topic.get(stat.exam_id)
            stat.subject_code = subject_code
            stat.percentage_w_assess = exam_to_percentage.get(stat.exam_id)

        for subject_code, totals in subject_totals.items():
            if totals['total_percentage_w_assess'] > 0:
                totals['passing_rate'] = round((totals['total_contribution'] / totals['total_percentage_w_assess']) * 100, 2)
            else:
                totals['passing_rate'] = 0.0

        total_percentage_w_assess = sum(totals['total_percentage_w_assess'] for totals in subject_totals.values())
        total_contribution = sum(totals['total_contribution'] for totals in subject_totals.values())

        if total_percentage_w_assess > 0:
            score_percentages = round((total_contribution / total_percentage_w_assess) * 100, 2)
        else:
            score_percentages = 0.0

        subjects = {assessment.subject.subject_code for assessment in assessments}

    except Students.DoesNotExist:
        stud_stats = []
        full_name = None
        assessment_counts = []
        score_percentages = 0.0
        total_percentage_w_assess = 0
        total_contribution = 0
        subjects = set()
        subject_totals = {}

    context = {
        'stud_stats': stud_stats,
        'full_name': full_name,
        'studentid': studentid,
        'studentschoolid' : studentschoolid,
        'assessment_counts': assessment_counts,
        'score_percentages': score_percentages,
        'total_percentage_w_assess': total_percentage_w_assess,
        'total_contribution': round(total_contribution, 1),
        'subjects': subjects,
        'subject_totals': subject_totals,
    }

    return render(request, 'assets/examchecker_all_stats_assessment.html', context)







@login_required(login_url='loginpage')
def students_all_stats_tos(request, studentid):
    try:
        student = Students.objects.get(studentid=studentid)

        stud_stats_tos = StudentStatsTos.objects.filter(student=student)
        
        firstname = student.firstname
        lastname = student.lastname

        student_topic_subtopic_counts = {}
        total_contribution = 0
        total_percentage_w_per_row = 0
        passing_rate = 0
        overall_contribution = 0
        overall_percentage_weight = 0
        overall_passing_rate = 0

        for stat in stud_stats_tos:
            subject = stat.subtopic.topic_subtopic.subject_topic
            subject_name = subject.subject_name
            subject_pw = subject.subject_pw
            subject_code = subject.subject_code
            topic_name = stat.subtopic.topicname
            subtopic_name = stat.subtopic.subtopic_name
            full_name = f"{student.firstname} {student.lastname}"
            
            if full_name not in student_topic_subtopic_counts:
                student_topic_subtopic_counts[full_name] = {}
            if subject_name not in student_topic_subtopic_counts[full_name]:
                student_topic_subtopic_counts[full_name][subject_name] = {
                    'subject_pw': subject_pw,
                    'subject_code': subject_code,
                    'topics': {},
                    'total_contribution': 0,
                    'total_percentage_w_per_row': 0,
                    'passing_rate': 0
                }
            if topic_name not in student_topic_subtopic_counts[full_name][subject_name]['topics']:
                student_topic_subtopic_counts[full_name][subject_name]['topics'][topic_name] = {}
            if subtopic_name not in student_topic_subtopic_counts[full_name][subject_name]['topics'][topic_name]:
                student_topic_subtopic_counts[full_name][subject_name]['topics'][topic_name][subtopic_name] = {
                    'question_count': 0,
                    'correct_count': 0,
                    'percentage_w_per_row': stat.percentage_w_per_row,  
                    'contribution': stat.contribution 
                }
            student_topic_subtopic_counts[full_name][subject_name]['topics'][topic_name][subtopic_name]['question_count'] += stat.question_count
            student_topic_subtopic_counts[full_name][subject_name]['topics'][topic_name][subtopic_name]['correct_count'] += stat.correct_count
            student_topic_subtopic_counts[full_name][subject_name]['total_contribution'] += stat.contribution
            if stat.percentage_w_per_row is not None:
                student_topic_subtopic_counts[full_name][subject_name]['total_percentage_w_per_row'] += stat.percentage_w_per_row

            overall_contribution += stat.contribution
            if stat.percentage_w_per_row is not None:
                overall_percentage_weight += stat.percentage_w_per_row

        for subject_data in student_topic_subtopic_counts[full_name].values():
            if subject_data['total_percentage_w_per_row'] > 0:
                subject_data['passing_rate'] = (subject_data['total_contribution'] / subject_data['total_percentage_w_per_row']) * 100

        if overall_percentage_weight > 0:
            overall_passing_rate = (overall_contribution / overall_percentage_weight) * 100
        
        context = {
            'student_topic_subtopic_counts': student_topic_subtopic_counts,
            'full_name': full_name,
            'firstname': firstname,
            'lastname': lastname,
            'studentid': student.studentid,
            'total_contribution': round(total_contribution, 2),
            'total_percentage_w_per_row': round(total_percentage_w_per_row, 2),
            'passing_rate': round(passing_rate, 2),
            'overall_contribution': round(overall_contribution, 2),
            'overall_percentage_weight': round(overall_percentage_weight, 2),
            'overall_passing_rate': round(overall_passing_rate, 2)
        }
    except Students.DoesNotExist:
        context = {
            'student_topic_subtopic_counts': {},
            'full_name': None,
            'studentid': None,
            'total_contribution': 0,
            'total_percentage_w_per_row': 0,
            'passing_rate': 0,
            'overall_contribution': 0,
            'overall_percentage_weight': 0,
            'overall_passing_rate': 0
        }
    return render(request, 'assets/examchecker_all_stats_tos.html', context)








@login_required(login_url='loginpage')
def display_scores_assessment(request, exam_id):
    scoress = StudentsScoreAssessment.objects.filter(exam_id = exam_id).first()
    scores = StudentsScoreAssessment.objects.filter(exam_id = exam_id).order_by('rank')
    context = {
        "scores": scores,
        "scoress" : scoress,
    }
    return render(request, "assets/examchecker_students_ranking_assessment.html", context)

@login_required(login_url='loginpage')
def display_scores_tos(request, exam_id, subject_name):
    scores = StudentsScoreTos.objects.filter(exam_id=exam_id).order_by('rank')
    
    context = {
        "scores": scores,
        "subject_name": subject_name,
    }
    
    return render(request, "assets/examchecker_students_ranking_tos.html", context)



@login_required(login_url='loginpage')
def restricted_list(request):
    query = request.GET.get('q', '')
    if query:
        restricted = Questionnaire.objects.filter(
            Q(status=1) &
            (Q(description__icontains=query) |
             Q(subject__subject_code__icontains=query))
        )
    else:
        restricted = Questionnaire.objects.filter(status=1)

    context = {
        "restricted": restricted,
        "q": query
    }
    return render(request, "assets/examchecker_restricted_list.html", context)


def remove_all_restricted(request):
    restricted = Questionnaire.objects.filter(status=1)

    for restrict in restricted:
        restrict.status = 0
        restrict.save()  
    
    return redirect('restricted_list')



def reports(request):
    reports = Reports.objects.all().order_by('-created_at')
    context = {'reports' : reports}
    return render(request, 'assets/reports.html', context)

@login_required(login_url='loginpage')
def reports_view_data(request, assessment_id):
    table_restrict_counts = TableRestrictCountsPerCategoryReports.objects.filter(assessment_id=assessment_id)
    
    c_n_w_per_items = CorrectAndWrongCountsPerItem.objects.filter(assessment_id=assessment_id).order_by('number')
    


    high_p_questions_reports = HighPQuestionsReports.objects.filter(assessment_id=assessment_id).order_by('-percentage')
    high_p_questions = Questionnaire.objects.filter(id__in=high_p_questions_reports.values('high_p_q'))
    
    low_p_questions_reports = LowPQuestionsReports.objects.filter(assessment_id=assessment_id).order_by('-percentage')
    low_p_questions = Questionnaire.objects.filter(id__in=low_p_questions_reports.values('low_p_q'))
    
    students_top5 = StudentsTop5.objects.filter(assessment_id=assessment_id)

    context = {
        'c_n_w_per_items' : c_n_w_per_items,
        'table_restrict_counts': table_restrict_counts,
        'high_p_questions': high_p_questions_reports,
        'low_p_questions': low_p_questions_reports,
        'high_p_questionnaire': high_p_questions,
        'low_p_questionnaire': low_p_questions,
        'students_top5': students_top5,
        'assessment_id' : assessment_id,
    }

    return render(request, 'assets/reports_view_data.html', context)


# ==============HTMX===============

@login_required(login_url='loginpage')
def subject(request):
    subject_id = request.GET.get('subject')
    topics = Topic.objects.filter(subject_topic_id=subject_id)
    context = {'topics': topics}
    return render(request, 'partials/topic.html', context)

@login_required(login_url='loginpage')
def topic(request):
    topic_id = request.GET.get('topic')
    subtopics = Subtopic.objects.filter(topic_subtopic_id=topic_id)
    context = {'subtopics': subtopics}
    return render(request, 'partials/subtopic.html', context)

@login_required(login_url='loginpage')
def subjectcreate(request):
    subject_id = request.GET.get('subjectcreate')
    topicscreate = Topic.objects.filter(subject_topic_id=subject_id)
    context = {'topicscreate': topicscreate}
    return render(request, 'partials/createquestion.html', context)

@login_required(login_url='loginpage')
def topiccreate(request):
    topic_id = request.GET.get('topiccreate')
    subtopicscreate = Subtopic.objects.filter(topic_subtopic_id=topic_id)
    context = {'subtopicscreate': subtopicscreate}
    return render(request, 'partials/createquestiontopic.html', context)


# ==============AJAX ASSESSMENT===============


def get_topics(request, subject_id):
    try:
        topics = Topic.objects.filter(subject_topic__id=subject_id)
        topic_list = [{'id': topic.id, 'topic_name': topic.topic_name} for topic in topics]
        return JsonResponse({'topics': topic_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_subtopics(request, topic_id):
    try:
        subtopics = Subtopic.objects.filter(topic_subtopic__id=topic_id)
        subtopic_list = [{'id': subtopic.id, 'subtopic_name': subtopic.subtopic_name} for subtopic in subtopics]
        return JsonResponse({'subtopics': subtopic_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

# ==============AJAX LEAVE PAGE===============

def clear_answer_keys_tos(request):
    if request.method == 'POST':
        global answer_keys_tos
        answer_keys_tos = []
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'}, status=400)

def clear_answer_keys_assessment(request):
    if request.method == 'POST':
        global answer_keys
        answer_keys = []
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'}, status=400)