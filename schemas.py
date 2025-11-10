"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# AI YouTube automation job schema
class VideoJob(BaseModel):
    """
    Video automation jobs for YouTube content generation
    Collection name: "videojob"
    """
    niche: str = Field(..., description="Target niche or topic area")
    title: str = Field(..., description="Selected video title")
    keywords: List[str] = Field(default_factory=list, description="SEO keywords")
    style: str = Field("educational", description="Narration style: educational, storytelling, listicle, news")
    duration: int = Field(60, ge=30, le=900, description="Target duration in seconds")
    outline: List[str] = Field(default_factory=list, description="High-level outline sections")
    script: str = Field("", description="Generated script text")
    status: str = Field("generated", description="Status of the job")
    audio_url: Optional[str] = Field(None, description="URL to generated voice-over audio")
    thumbnail_url: Optional[str] = Field(None, description="URL to generated thumbnail image")
    youtube_url: Optional[str] = Field(None, description="Published YouTube video URL if uploaded")
    upload_status: Optional[str] = Field(None, description="Upload progress status")
