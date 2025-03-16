import mimetypes
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas import schema
from app.crud import categorycrud as crud
from app.bgtask import task
from starlette.concurrency import run_in_threadpool

FILES_DIR = Path("media")

router = APIRouter(prefix='/category', tags=["Category"])

# ✅ Get Category by id +
@router.get("/{category_id}", response_model=schema.ReturnCategoryWithImages)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    try:
        # Retrieve the full category ORM object
        category_obj = await run_in_threadpool(crud.get_category_by_id, db, category_id)
        if not category_obj:
            raise HTTPException(status_code=404, detail=f"Category {category_id} not found")

        # Get the main image ORM object
        main_img_obj = await run_in_threadpool(crud.image_main_check_by_category_id, db, category_id)
        # Get images list (ORM objects)
        images_obj = await run_in_threadpool(crud.get_image_by_category_id, db, category_id)

        # Build the response dictionary manually
        response_data = {
            "id": category_obj.id,
            "category_name": category_obj.category_name,
            # Instead of assigning to the relationship, we set a separate key
            "main_image": main_img_obj.name_base64 if main_img_obj else None,
            "description": category_obj.description,
            # Convert stored comma-separated skills into a list
            "skill": category_obj.skill.split(",") if category_obj.skill else [],
            "images": images_obj,  # Pydantic will use the alias in ReturnImageWithCategory
        }
        return response_data

    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error {str(e)}")



# ✅ Get all categories +
@router.get("s/", response_model=list[schema.ReturnCategories])
async def get_categories(db: Session = Depends(get_db)):
    try:
        categories = await run_in_threadpool(crud.get_categories, db)

        if not categories:
            raise HTTPException(status_code=404, detail="Categories not found")

        result = []
        for cat in categories:
            main_img = await run_in_threadpool(crud.image_main_check_by_category_id, db, cat.id)
            # result.append({
            #     "id": cat.id,
            #     "category_name": cat.category_name,
            #     "title": cat.title,
            #     "main_image": main_img.name_base64 if main_img else None,
            #     "description": cat.description,
            #     "skill": cat.skill.split(",") if cat.skill else []
            # })
            result.append(schema.ReturnCategories(
                id=cat.id,
                category_name=cat.category_name,
                main_image=main_img.name_base64 if main_img else None,
            ))
        return result
    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error {str(e)}")


# ✅ Create Category +
@router.post("/", response_model=schema.Category)
async def create_category(category: schema.Category = Depends(task.get_category)):
    try:
        return category
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error {str(e)}")

# ✅ Delete Category +
@router.delete("/{category_id}")
async def del_category(category_id: int, db: Session = Depends(get_db)):
    try:
        result = await run_in_threadpool(crud.del_category, db, category_id)
        return result

    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Server error")

# ✅ Change or Create main image +
@router.put("/main-image/{category_id}")
async def change_main_img(category_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        base64_img = await task.file_to_base(file)
        result = await run_in_threadpool(crud.change_main_img, db, base64_img, category_id)
        return result
    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Server error")

# ✅ Create image for category +
@router.post("/image/{category_id}")
async def create_img(category_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    base64_img = await task.file_to_base(file)

    check_category = await run_in_threadpool(crud.get_category_by_id, db, category_id)
    if not check_category:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")

    existing_image = await run_in_threadpool(crud.check_image_by_base64, db, base64_img)
    if existing_image:
        raise HTTPException(status_code=400, detail="Image with the same base64 string already exists")

    try:
        img_data = schema.CreateImage(
            name=file.filename,
            name_base64=base64_img,
            category_id=category_id
        )

        new_image = await run_in_threadpool(crud.create_image, db, img_data)

        return "Image created successfully"
    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error {str(e)}")


# ✅ Delete image by id +
@router.delete("/image/{image_id}")
async def del_image(image_id: int, db: Session = Depends(get_db)):
    try:
        result = await run_in_threadpool(crud.del_image, db, image_id)
        return result

    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error {str(e)}")

# ✅ Get image by id +
@router.get("/image/{image_id}", response_model=schema.Image)
async def get_image(image_id: int, db: Session = Depends(get_db)):
    try:
        image = await run_in_threadpool(crud.get_image_by_id, db, image_id)
        if not image:
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
        return image

    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error {str(e)}")

# ✅ Get all images for a category send one image +
@router.get("/images/{category_id}", response_model=list[schema.Image])
async def get_image(category_id: int, db: Session = Depends(get_db)):
    try:
        images = await run_in_threadpool(crud.get_images_by_category_id, db, category_id)
        if not images:
            raise HTTPException(status_code=404, detail=f"Images for category {category_id} not found")
        return images

    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Server error")
