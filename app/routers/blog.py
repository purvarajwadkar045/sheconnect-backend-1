from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Blog
from app.schemas.schemas import BlogCreate
from typing import List, Dict, Any

router = APIRouter(prefix="/blogs", tags=["Blogs"])

@router.post("/create", status_code=201)
def create_blog(
    blog_data: BlogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new blog post.
    """
    new_blog = Blog(
        user_id=current_user.user_id,
        title=blog_data.title,
        content=blog_data.content
    )
    
    db.add(new_blog)
    db.commit()
    db.refresh(new_blog)
    
    return {
        "message": "Blog created successfully",
        "blogId": new_blog.blog_id
    }

@router.get("/", status_code=200)
def get_all_blogs(db: Session = Depends(get_db)):
    """
    Returns all blog posts.
    """
    # Fetch all active blogs
    blogs = db.query(Blog).filter(Blog.is_active == True).all()
    
    response_data = []
    for blog in blogs:
        response_data.append({
            "id": blog.blog_id,
            "title": blog.title,
            "content": blog.content
        })
        
    return {"blogs": response_data}
