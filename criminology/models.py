from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.db.models import Sum


class AcademicYear(models.Model):
    id = models.AutoField(primary_key=True)
    year_series = models.CharField(max_length=20)
    period = models.CharField(max_length=200)
    status = models.IntegerField(default=0)

    def __str__(self):
      return f"{self.year_series} - {self.period}"


class Students(models.Model):
    id = models.AutoField(primary_key=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, null=True, blank=True)
    studentschoolid = models.IntegerField(unique=True, null=True, blank=True)
    lastname = models.CharField(max_length=200)
    firstname = models.CharField(max_length=200)
    studentid = models.IntegerField(unique=True)

    def __str__(self):
      return str(self.studentid)


class Subject(models.Model):
    id = models.AutoField(primary_key=True)
    subject_name = models.CharField(max_length=50)
    subject_code = models.CharField(max_length=10, null=True)
    subject_pw = models.IntegerField(default=0)
    
    def __str__(self):
      return self.subject_name

class Topic(models.Model):
    id = models.AutoField(primary_key=True)
    subject_topic = models.ForeignKey(Subject, on_delete=models.CASCADE)
    topic_name = models.CharField(max_length=200)

    @property
    def subjectname(self):
      return self.subject_topic.subject_name

    @property
    def subjectcode(self):
      return self.subject_topic.subject_code

    def __str__(self):
      return self.topic_name


class Subtopic(models.Model):
    id = models.AutoField(primary_key=True)
    topic_subtopic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    subtopic_name = models.CharField(max_length=200)

    @property
    def topicname(self):
      return self.topic_subtopic.topic_name

    def __str__(self):
      return self.subtopic_name


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    category = models.CharField(max_length=50)

    def __str__(self):
      return self.category



class TableOfSpecification(models.Model):
    id = models.AutoField(primary_key=True)
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)  
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, null=True, blank=True) 
    subtopic = models.ForeignKey('Subtopic', on_delete=models.CASCADE, null=True, blank=True)

    group_id = models.IntegerField(db_index=True)
    row_id = models.IntegerField(null=True, blank=True)
    pwd = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    understanding = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    remembering = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    analyzing = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    creating = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    evaluating = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    applying = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    def __str__(self):
        return f"TOS for {self.subject.subject_name} - Topic: {self.topic.topic_name if self.topic else 'N/A'}"

    @property
    def totals_calculated(self):
        return self.understanding + self.remembering + self.analyzing + self.creating + self.evaluating + self.applying

class PercentageWeightPerTos(models.Model):
    pwd = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    row_id = models.IntegerField(null=True, blank=True)
    group_id = models.IntegerField(null=True, blank=True)
    def __str__(self):
      return str(self.row_id)

  
class Assessment(models.Model):
    id = models.AutoField(primary_key=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, blank=True)
    competencies = models.ForeignKey(Subtopic, on_delete=models.CASCADE, null=True, blank=True)
    assessment_id = models.IntegerField(null=True, blank=True, db_index=True)

    remembering = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    understanding = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    applying = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    analyzing = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    evaluating = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    creating = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))

    def __str__(self):
        return str(self.assessment_id)
  

class PercentageWeightPerAssessment(models.Model):
    status = models.IntegerField(default=0)
    percentage_w_assess = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    assessment_id = models.IntegerField(null=True, blank=True)



class Questionnaire(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True)
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, null=True)
    description = models.CharField(max_length=600)
    correct_answer = models.CharField(max_length=200)
    distructor1 = models.CharField(max_length=200)
    distructor2 = models.CharField(max_length=200)
    distructor3 = models.CharField(max_length=200)
    status = models.IntegerField(default=0)
    
    def __str__(self):
      return self.description


class AnswerKeyAssessment(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, null=True, blank=True)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    question = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE ,null=True, blank=True)
    category = models.CharField(max_length=20, null=True, blank=True)
    assessment_exam_id = models.IntegerField(null=True, blank=True)
    a = models.CharField(max_length=300, null=True, blank=True)
    b = models.CharField(max_length=300, null=True, blank=True)
    c = models.CharField(max_length=300, null=True, blank=True)
    d = models.CharField(max_length=300, null=True, blank=True)
    number = models.IntegerField(null=True, blank=True)
    correct_choice = models.CharField(max_length=1)
    correct_answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=0)

    def __str__(self):
        return str(self.assessment_exam_id)

class AnswerKeyTableOfSpecification(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, null=True, blank=True)
    tableofspecification = models.ForeignKey(TableOfSpecification, on_delete=models.CASCADE)
    question = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE ,null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE ,null=True, blank=True)
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE ,null=True, blank=True)
    category = models.CharField(max_length=20, null=True, blank=True)
    number = models.IntegerField(null=True, blank=True)
    row_id = models.IntegerField(null=True, blank=True)
    tos_exam_id = models.IntegerField(null=True, blank=True)
    a = models.CharField(max_length=300, null=True, blank=True)  
    b = models.CharField(max_length=300, null=True, blank=True)
    c = models.CharField(max_length=300, null=True, blank=True)
    d = models.CharField(max_length=300, null=True, blank=True)
    correct_choice = models.CharField(max_length=1)
    correct_answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=0)


    def __str__(self):
      return str(self.tos_exam_id)

class StudentsScoreTos(models.Model):
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(AnswerKeyTableOfSpecification, on_delete=models.CASCADE ,null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    exam_id = models.IntegerField(null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)
    lastname = models.CharField(max_length=200,null=True, blank=True)
    firstname = models.CharField(max_length=200,null=True, blank=True)
    studentid = models.IntegerField(null=True, blank=True)
    period = models.CharField(max_length=200,null=True, blank=True)

    def __str__(self):
      return str(self.studentid)

class StudentsScoreAssessment(models.Model):
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(AnswerKeyAssessment, on_delete=models.CASCADE, null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    exam_id = models.IntegerField(null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)
    lastname = models.CharField(max_length=200, null=True, blank=True)
    firstname = models.CharField(max_length=200, null=True, blank=True)
    studentid = models.IntegerField(null=True, blank=True)
    period = models.CharField(max_length=200, null=True, blank=True)


    def __str__(self):
        return str(self.studentid)
    

class CategoriesCountPercentage(models.Model):
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, null=True, blank=True)
    remembering = models.IntegerField()
    creating = models.IntegerField()
    understanding = models.IntegerField()
    applying = models.IntegerField()
    analyzing = models.IntegerField()
    evaluating = models.IntegerField()

    remembering_correct_total = models.IntegerField(null=True, blank=True)
    creating_correct_total = models.IntegerField(null=True, blank=True)
    understanding_correct_total = models.IntegerField(null=True, blank=True)
    applying_correct_total = models.IntegerField(null=True, blank=True)
    analyzing_correct_total = models.IntegerField(null=True, blank=True)
    evaluating_correct_total = models.IntegerField(null=True, blank=True)

    @property
    def calculate_remembering_percentage(self):
        return (self.remembering_correct_total / self.remembering) * 100 if self.remembering else 0
    
    @property
    def calculate_creating_percentage(self):
        return (self.creating_correct_total / self.creating) * 100 if self.creating else 0
    
    @property
    def calculate_understanding_percentage(self):
        return (self.understanding_correct_total / self.understanding) * 100 if self.understanding else 0
    
    @property
    def calculate_applying_percentage(self):
        return (self.applying_correct_total / self.applying) * 100 if self.applying else 0
    
    @property
    def calculate_analyzing_percentage(self):
        return (self.analyzing_correct_total / self.analyzing) * 100 if self.analyzing else 0
    
    @property
    def calculate_evaluating_percentage(self):
        return (self.evaluating_correct_total / self.evaluating) * 100 if self.evaluating else 0
    
    @property
    def calculate_overall_percentage(self):
        total = (self.remembering + self.creating + self.understanding +
                 self.applying + self.analyzing + self.evaluating)
        correct_total = (self.remembering_correct_total + self.creating_correct_total + 
                         self.understanding_correct_total + self.applying_correct_total + 
                         self.analyzing_correct_total + self.evaluating_correct_total)
        return (correct_total / total) * 100 if total else 0

    def __str__(self):
        return str(self.academic_year)




class StudentStatsTos(models.Model):
    
    student = models.ForeignKey('Students', on_delete=models.CASCADE)
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE)
    tos_exam = models.ForeignKey('AnswerKeyTableOfSpecification', on_delete=models.CASCADE)
    lastname = models.CharField(max_length=200, null=True, blank=True)
    firstname = models.CharField(max_length=200, null=True, blank=True)
    question_count = models.IntegerField(default=0)
    correct_count = models.IntegerField(default=0)
    row_id = models.IntegerField(default=0)

    @property
    def percentage_w_per_row(self):
        try:
            tos_rows = AnswerKeyTableOfSpecification.objects.filter(
                tos_exam_id=self.tos_exam.tos_exam_id, row_id=self.row_id
            )
            percentage_weights = PercentageWeightPerTos.objects.filter(
                row_id__in=[tos.row_id for tos in tos_rows]
            )
            weights = [pw.pwd for pw in percentage_weights if pw.pwd is not None]
            if weights:
                total_weight = sum(weights, Decimal("0"))
                average_weight = (total_weight / len(weights)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                return float(average_weight)
            return None
        except (AnswerKeyTableOfSpecification.DoesNotExist, PercentageWeightPerTos.DoesNotExist):
            return None


    @property
    def contribution(self):
        if self.question_count == 0:
            return 0.0
        percentage_weight = self.percentage_w_per_row
        if percentage_weight is None:
            return 0.0
        score_ratio = Decimal(self.correct_count) / Decimal(self.question_count)
        contribution = (score_ratio * Decimal(str(percentage_weight))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return float(contribution)

    @property
    def total_contribution(self):
        student_stats = StudentStatsTos.objects.filter(student=self.student)
        total = sum(stat.contribution for stat in student_stats)
        return round(total, 2)

    @property
    def total_percentage_w_per_row(self):
        student_stats = StudentStatsTos.objects.filter(student=self.student)
        total = sum(
            stat.percentage_w_per_row for stat in student_stats if stat.percentage_w_per_row is not None
        )
        return round(total, 2)


    @property
    def passing_rate(self):
        total_contribution = self.total_contribution
        total_percentage_w_per_row = self.total_percentage_w_per_row
        if total_percentage_w_per_row == 0:
            return 0
        return round((total_contribution / total_percentage_w_per_row) * 100, 2)

    def __str__(self):
        return f"{self.student}  - {self.row_id} - {self.subtopic}"




class StudentStatsAssessment(models.Model):
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey('Students', on_delete=models.CASCADE, null=True, blank=True)
    exam_id = models.IntegerField(null=True, blank=True)
    total_questions_taken = models.IntegerField()
    total_questions_score = models.IntegerField()

    assessment_taken_count = models.IntegerField(null=True, blank=True)
    curr_assess_percentage = models.IntegerField(null=True, blank=True)
    final_assess_percentage = models.FloatField(null=True, blank=True)

    @property
    def total_questions_taken_sum(self):
        result = StudentStatsAssessment.objects.filter(student=self.student).aggregate(total=Sum('total_questions_taken'))
        return result.get('total', 0) if result else 0

    @property
    def total_questions_score_sum(self):
        return StudentStatsAssessment.objects.filter(student=self.student).aggregate(total=Sum('total_questions_score'))['total'] or 0

    @property
    def assessment_taken_count_calculated(self):
        return int(self.total_questions_taken_sum / 100 if self.total_questions_taken_sum is not None else 0)

    @property
    def contribution(self):
        pwa = PercentageWeightPerAssessment.objects.filter(assessment_id=self.exam_id).first()
        if pwa and self.total_questions_taken != 0:
            percentage_weight = float(pwa.percentage_w_assess)
            contribution = (self.total_questions_score / self.total_questions_taken) * percentage_weight
            return round(contribution, 1)
        return 0

    @property
    def score_percentage(self):
        stud_stats = StudentStatsAssessment.objects.filter(student=self.student)

        total_percentage_w_assess = sum(
            float(
                PercentageWeightPerAssessment.objects.filter(assessment_id=stat.exam_id, status=0)
                .first()
                .percentage_w_assess
            )
            for stat in stud_stats
            if PercentageWeightPerAssessment.objects.filter(assessment_id=stat.exam_id, status=0).exists()
        )

        total_contribution = sum(stat.contribution for stat in stud_stats if stat.contribution is not None)
        
        if total_percentage_w_assess == 0:
            return 0
        
        percentage = (total_contribution / total_percentage_w_assess) * 100
        return round(percentage, 1)

    def __str__(self):
        return str(self.student.studentid)


class SubjectCountPercentage(models.Model):
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True)
    total_q_counts_per_subject = models.IntegerField()
    total_correct_counts_per_subject = models.IntegerField()

    def calculate_cor_percentage(self):
        return (self.total_correct_counts_per_subject / self.total_q_counts_per_subject) * 100 if self.total_q_counts_per_subject else 0
    
    def __str__(self):
      return str(self.subject)
    
    
class TableRestrictCountsPerCategoryReports(models.Model):
    assessment_id = models.IntegerField(null=True, blank=True)

    remembering = models.IntegerField()
    creating = models.IntegerField()
    understanding = models.IntegerField()
    applying = models.IntegerField()
    analyzing = models.IntegerField()
    evaluating = models.IntegerField()
    
class HighPQuestionsReports(models.Model):
    assessment_id = models.IntegerField(null=True, blank=True)

    high_p_q = models.CharField(max_length=200, null=True, blank=True)
    number = models.IntegerField()
    percentage = models.FloatField()

class LowPQuestionsReports(models.Model):
    assessment_id = models.IntegerField(null=True, blank=True)

    low_p_q = models.CharField(max_length=200, null=True, blank=True)
    number = models.IntegerField()
    percentage = models.FloatField()

class StudentsTop5(models.Model):
    assessment_id = models.IntegerField(null=True, blank=True)

    first_name = models.CharField(max_length=200, null=True, blank=True)
    lastname = models.CharField(max_length=200, null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)


class Reports(models.Model):
    assessment_id = models.IntegerField(null=True, blank=True)
    

    percentage_weight = models.IntegerField(null=True, blank=True)
    subject = models.CharField(max_length=200, null=True, blank=True)
    topic = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CorrectAndWrongCountsPerItem(models.Model):
    assessment_id = models.IntegerField(null=True, blank=True)
    number = models.IntegerField()
    question_description = models.CharField(max_length=200, null=True, blank=True)
    correct_counts = models.IntegerField()
    wrong_counts = models.IntegerField()


class AssessmentRecordsDashboard(models.Model):
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, null=True, blank=True)
    topic = models.CharField(max_length=200, null=True, blank=True)
    subject_code = models.CharField(max_length=200, null=True, blank=True)

    assessment_id = models.IntegerField(null=True, blank=True)

    remembering = models.IntegerField()
    creating = models.IntegerField()
    understanding = models.IntegerField()
    applying = models.IntegerField()
    analyzing = models.IntegerField()
    evaluating = models.IntegerField()
    category_total = models.IntegerField(null=True, blank=True)

    remembering_correct_total = models.IntegerField(null=True, blank=True)
    creating_correct_total = models.IntegerField(null=True, blank=True)
    understanding_correct_total = models.IntegerField(null=True, blank=True)
    applying_correct_total = models.IntegerField(null=True, blank=True)
    analyzing_correct_total = models.IntegerField(null=True, blank=True)
    evaluating_correct_total = models.IntegerField(null=True, blank=True)
    category_correct_total = models.IntegerField(null=True, blank=True)


    @property
    def calculate_remembering_percentage(self):
        return (self.remembering_correct_total / self.remembering) * 100 if self.remembering else 0
    
    @property
    def calculate_creating_percentage(self):
        return (self.creating_correct_total / self.creating) * 100 if self.creating else 0
    
    @property
    def calculate_understanding_percentage(self):
        return (self.understanding_correct_total / self.understanding) * 100 if self.understanding else 0
    
    @property
    def calculate_applying_percentage(self):
        return (self.applying_correct_total / self.applying) * 100 if self.applying else 0
    
    @property
    def calculate_analyzing_percentage(self):
        return (self.analyzing_correct_total / self.analyzing) * 100 if self.analyzing else 0
    
    @property
    def calculate_evaluating_percentage(self):
        return (self.evaluating_correct_total / self.evaluating) * 100 if self.evaluating else 0
    
    @property
    def calculate_overall_percentage(self):
        total = (self.remembering + self.creating + self.understanding +
                 self.applying + self.analyzing + self.evaluating)
        correct_total = (self.remembering_correct_total + self.creating_correct_total + 
                         self.understanding_correct_total + self.applying_correct_total + 
                         self.analyzing_correct_total + self.evaluating_correct_total)
        return (correct_total / total) * 100 if total else 0