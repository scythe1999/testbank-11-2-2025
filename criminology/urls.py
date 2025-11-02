from django.urls import path
from . import views

urlpatterns = [
     # ========== LOGINPAGE =============
    path('login/', views.login_view, name='loginpage'),
    path('logout/', views.logout, name='logout'),
    
    # ========== ASSETS =============
    path('', views.homepage, name='homepage'),
    path('restrict-remove/<int:id>/', views.restrictquestionremove, name='restrictquestionremove'),
    path('homepage/endpoint/', views.endpoint, name='endpoint'),

    # ========== AJAX =============
    path('get_topics/<int:subject_id>/', views.get_topics, name='get_topics'),
    path('get_subtopics/<int:topic_id>/', views.get_subtopics, name='get_subtopics'),

    # ========== QUESTIONNAIRES =============
    path('questionnaires/', views.questionnaires, name='questionnaires'),
    path('questionnaires/create', views.questionnairescreate, name='questionnairescreate'),
    path('questionnaires/restrict-question/<int:id>', views.restrictquestion, name='restrictquestion'),
    path('questionnaires/addquestion/', views.addquestion, name='addquestion'),
    path('questionnaires/delete/<int:id>/', views.delete, name='delete'),
    path('questionnaires/update/<int:id>/', views.update, name='update'),
    path('questionnaires/updatequestion/<int:id>/', views.updatequestion, name='updatequestion'), 
    path('questionnaires/print-table-of-specification/<int:group_id>/', views.print_questionnaire, name='print_questionnaire'),
    path('questionnaires/print-table-of-specification/view-table/<int:group_id>/', views.print_questionnaire_view_table, name='print_questionnaire_view_table'), 
    path('questionnaires/print-assessment/<int:assessment_id>/', views.print_assessment, name='print_assessment'),
    path('questionnaires/print-assessment/view-table-assessment/<int:assessment_id>/', views.print_questionnaire_view_table_assessment, name='print_questionnaire_view_table_assessment'), 
    path('questionnaires/print-exam-sheet', views.print_final_nav, name='print_final_nav'),
    path('questionnaires/print-generated-assessment/<int:assessment_exam_id>/', views.print_generated_assessment, name='print_generated_assessment'),
    path('questionnaires/print-generated-table-of-specification/<int:tos_exam_id>/', views.print_generated_tableOfSpecification, name='print_generated_tableOfSpecification'),

    # ========== MASTERFILE =============
    path('masterfile/students/', views.masterfilestudents, name='masterfilestudents'),
    path('masterfile/students/upload_csv/', views.upload_csv, name='upload_csv'), 
    path('masterfile/students/process_csv_data/', views.process_csv_data, name='process_csv_data'),
    path('masterfile/students/export_students/', views.export_students, name='export_students'),
    path('masterfile/students/create/', views.masterfilestudentscreate, name='masterfilestudentscreate'),
    path('masterfile/students/update/<int:pk>/', views.masterfilestudentsupdate, name='masterfilestudentsupdate'),
    path('masterfile/students/cancel-student-update', views.student_cancel_update, name='student_cancel_update'),
    path('masterfile/students/delete/<int:id>/', views.deletestudent, name='deletestudent'),
    path('masterfile/academic-year/', views.academic_year, name='academic_year'),
    path('masterfile/table-of-specification/', views.table_of_specification, name='table_of_secification'),
    path('masterfile/table-of-specification/delete/<int:group_id>/', views.table_of_specification_delete, name='table_of_specification_delete'),
    path('masterfile/table-of-specification/update/<int:group_id>/', views.table_of_specification_update, name='table_of_specification_update'),
    path('submit/<int:group_id>/', views.submit_table_of_specification, name='submit_table_of_specification'),
    path('masterfile/table-of-specification/create/<int:pk>/', views.table_of_secificationcreate, name='table_of_secificationcreate'),
    path('masterfile/Assessment/', views.assessment, name='assessment'),
    path('masterfile/Assessment/create', views.assessment_create, name='assessmentcreate'),
    path('masterfile/Assessment/update/<int:assessment_id>/', views.assessment_update, name='assessmentupdate'),
    path('masterfile/Assessment/delete/<int:assessment_id>/', views.assessment_delete, name='assessmentdelete'),
    path('masterfile/academic-year/create/', views.academicyearcreate, name='academicyearcreate'),
    path('masterfile/academic-year/update/<int:pk>/', views.academicyearupdate, name='academicyearupdate'),
    path('masterfile/', views.modulessubject, name='modules'),
    path('masterfile/subjects/', views.modulessubject, name='modulessubject'),
    path('masterfile/topic/', views.modulestopic, name='modulestopic'),
    path('masterfile/subtopic/', views.modulessubtopic, name='modulessubtopic'),
    path('masterfile/subjects/update/<int:pk>/', views.modulessubjectupdate, name='modulessubjectupdate'),
    path('masterfile/subjects/update/final/<int:pk>/', views.modulessubjectupdatefinal, name='modules_update_subject_final'),
    path('masterfile/subjects/delete/<int:pk>/', views.modulessubjectdelete, name='modulessubjectdelete'),
    path('masterfile/topics/update/<int:pk>/', views.modulestopicupdate, name='modulestopicupdate'),
    path('masterfile/topics/update/final/<int:pk>/', views.modulestopicupdatefinal, name='modules_update_topic_final'),
    path('masterfile/topics/delete/<int:pk>', views.modulestopicdelete, name='modulestopicdelete'),
    path('masterfile/subtopics/update/<int:pk>/', views.modulessubtopicupdate, name='modulessubtopicupdate'),
    path('masterfile/subtopics/update/final/<int:pk>/', views.modulessubtopicupdatefinal, name='modules_update_subtopic_final'),
    path('masterfile/subtopics/delete/<int:pk>/', views.modulessubtopicdelete, name='modulessubtopicdelete'),
    



    # ========== QUESTIONNAIRE GENERATE =============  
    path('assessment/save_answer_key/', views.save_answer_key, name='save_answer_key'),
    path('export-answerkey/<int:assessment_id>', views.export_answerkey, name='export_answerkey'),
    path('export-answerkey-qualifying/<int:exam_id>', views.export_answerkey_tos, name='export_answerkey_tos'),
    path('assessment/save_answer_key_tos/', views.save_answer_key_toss, name='save_answer_key_toss'),
    path('masterfile/table-of-specification/save_answer_key', views.save_answer_key_tos, name='save_answer_key_tos'),
    path('masterfile/students/display-scores-and-rank/assessment/<int:exam_id>/', views.display_scores_assessment, name='display_scores_assessment'),
    path('masterfile/students/display-scores-and-rank/tos/<int:exam_id>/<str:subject_name>', views.display_scores_tos, name='display_scores_tos'),

    # ========== EXAM CHECKER =============
    path('exam-checker/table-of-scpecification/', views.check_tos, name='check_tos'),
    path('exam-checker/assessment/', views.check_assessment, name='check_assessment'),
    path('import-csv/table-of-scpecification/upload-csv/<int:tos_exam_id>/', views.import_csv_tos, name="import_csv_tos"),
    path('import-csv/assessment/upload-csv/<int:assessment_exam_id>/', views.import_csv_assessment, name="import_csv_assessment"),
    path('save-data/table-of-scpecification/', views.save_data_tos, name='save_data_tos'),
    path('save-data/assessment/', views.save_data_assessment, name='save_data_assessment'),
    path('restricted-list-data/', views.restricted_list, name='restricted_list'),
    path('restricted-list-remove/', views.remove_all_restricted, name='remove_all_restricted'),
    path('exam-checker/students-ranking&scores/', views.rankings_scores, name='rankings_scores'),
    path('exam-checker/students-stats/', views.students_stats, name='students_stats'),
    path('exam-checker/students_all_stats_assessment/<int:studentid>', views.students_all_stats_assessment, name='students_all_stats_assessment'),
    path('exam-checker/students_all_stats_tos/<int:studentid>', views.students_all_stats_tos, name='students_all_stats_tos'),

    # ========== EXAM CHECKER =============
    path('reports/', views.reports, name='reports'),
    path('reports/view-data/<int:assessment_id>', views.reports_view_data, name='reports_view_data'),
     

     
    
    # ========== CLEAR ANSWER KEY IF LEAVE THE PAGE =============
    path('clear-answer-keys-tos/', views.clear_answer_keys_tos, name='clear_answer_keys_tos'),

    # ========== HTMX =============
    path('subject-create/', views.subjectcreate, name='subjectcreate'),
    path('topic-create/', views.topiccreate, name='topiccreate'),
    path('subject/', views.subject, name='subject'),
    path('topics/', views.topic, name='topic'),
    path('masterfile/create-subject/', views.modules_create_subject, name='modules_create_subject'),
    path('masterfile/create-subject-final/', views.modules_create_subject_final, name='modules_create_subject_final'),
    path('masterfile/create-topic/', views.modules_create_topic, name='modules_create_topic'),
    path('masterfile/create-topic-final/', views.modules_create_topic_final, name='modules_create_topic_final'),
    path('masterfile/create-subtopic/', views.modules_create_subtopic, name='modules_create_subtopic'),
    path('masterfile/create-subtopic-final/', views.modules_create_subtopic_final, name='modules_create_subtopic_final'),
   ]