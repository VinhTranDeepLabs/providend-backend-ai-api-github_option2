from config.questions import PRESET_QUESTIONS, CATEGORIZED_QUESTIONS
from models.schemas import QuestionAnswer
from typing import List, Dict, Any
import json

class QuestionTemplateService:
    def __init__(self):
        self.preset_questions = PRESET_QUESTIONS
        self.categorized_questions = CATEGORIZED_QUESTIONS

    def get_all_templates(self):
        return list(self.categorized_questions.keys())
    
    def get_question_template(self, template_name: str) -> List[str]:
        return self.categorized_questions.get(template_name, [])