from fastapi import APIRouter, Response, status
from services.question_template_service import QuestionTemplateService

router = APIRouter()

@router.get("/all")
async def get_all_question_templates():
    """
    get all question templates
    """
    # Placeholder implementation
    # create meeting object with advisor and clients
    result = QuestionTemplateService().get_all_templates()

    return {
        "templates": result,
    }


@router.get("/{template_name}")
async def get_question_template(template_name: str):
    """
    get a specific question template

    :param template_name: The template name
    :type template_name: str
    """
    # Placeholder implementation
    # update meeting object with new status
    result = QuestionTemplateService().get_question_template(template_name)

    return {
        "questions": result,
    }
