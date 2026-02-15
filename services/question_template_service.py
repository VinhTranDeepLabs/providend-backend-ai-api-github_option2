from utils.db_utils import DatabaseUtils
from config.questions import CATEGORIZED_QUESTIONS
from typing import List, Dict, Optional
import uuid


class QuestionTemplateService:
    def __init__(self, conn):
        self.db = DatabaseUtils(conn)

    def get_all_templates(self) -> List[Dict]:
        """List all question templates"""
        return self.db.list_question_templates()

    def get_detailed_template(self, template_id: str) -> Optional[Dict]:
        """Get a complete template with all sections and questions"""
        return self.db.get_detailed_template(template_id)

    def create_detailed_template(self, template_name: str, sections: Dict[str, List[str]], template_owner: str = None, template_id: str = None, template_type: str = "with-section") -> Dict:
        """Create a new template with all sections and questions"""
        if not template_id:
            template_id = str(uuid.uuid4())
        return self.db.create_detailed_template(template_id, template_name, sections, template_owner, template_type)

    def save_detailed_template(self, template_id: str, template_name: str, sections: Dict[str, List[str]], template_owner: str = None, template_type: str = None) -> Dict:
        """Save button — full replace of sections and questions"""
        return self.db.save_detailed_template(template_id, template_name, sections, template_owner, template_type)

    def delete_template(self, template_id: str) -> Dict:
        """Delete a template (cascades to sections and questions)"""
        return self.db.delete_question_template(template_id)

    def get_categorized_questions(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Returns the exact same format as CATEGORIZED_QUESTIONS from config/questions.py.
        Format: {meeting_type: {section_name: [question_strings]}}
        """
        return self.db.get_categorized_questions()

    def refresh_categorized_questions(self):
        """
        Reload CATEGORIZED_QUESTIONS from the database.
        Updates the global dict in-place so all modules that imported it see the new data.
        Falls back to the hardcoded defaults if DB has no data.
        """
        try:
            db_questions = self.db.get_categorized_questions()

            if db_questions:
                CATEGORIZED_QUESTIONS.clear()
                CATEGORIZED_QUESTIONS.update(db_questions)
                print(f"Refreshed CATEGORIZED_QUESTIONS from DB ({len(db_questions)} meeting types)")
            else:
                print("No question data in DB, keeping hardcoded defaults")
        except Exception as e:
            print(f"Failed to refresh CATEGORIZED_QUESTIONS from DB: {e}")
