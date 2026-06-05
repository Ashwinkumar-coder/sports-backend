import sys
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models.user import User
from app.models.department import Department
from app.models.federation import Federation
from app.core import security

def seed():
    print("Creating all tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Checking for Super Admin...")
        super_admin = db.query(User).filter(User.role == "super_admin").first()
        if not super_admin:
            super_admin = User(
                email="superadmin@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="Platform Super Admin",
                role="super_admin",
                is_approved=True
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            print("Super Admin created: superadmin@sports.com (password123)")
        else:
            print("Super Admin already exists.")
            
        print("Checking for Department...")
        dept = db.query(Department).first()
        if not dept:
            dept = Department(
                name="National Cricket Council",
                created_by_id=super_admin.id
            )
            db.add(dept)
            db.commit()
            db.refresh(dept)
            print("National Cricket Council Department created.")
        else:
            print("Department already exists.")
            
        print("Checking for Department Admin...")
        dept_admin = db.query(User).filter(User.role == "department_admin").first()
        if not dept_admin:
            dept_admin = User(
                email="deptadmin@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="NCC Department Admin",
                role="department_admin",
                is_approved=True,
                department_id=dept.id
            )
            db.add(dept_admin)
            db.commit()
            db.refresh(dept_admin)
            print("Department Admin created: deptadmin@sports.com (password123)")
        else:
            print("Department Admin already exists.")
            
        print("Checking for Federation Admin...")
        fed_admin = db.query(User).filter(User.role == "federation_admin").first()
        if not fed_admin:
            fed_admin = User(
                email="fedadmin@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="State Cricket Association Admin",
                role="federation_admin",
                is_approved=True,
                department_id=dept.id
            )
            db.add(fed_admin)
            db.commit()
            db.refresh(fed_admin)
            print("Federation Admin created: fedadmin@sports.com (password123)")
        else:
            print("Federation Admin already exists.")
            
        print("Checking for Federation...")
        fed = db.query(Federation).first()
        if not fed:
            fed = Federation(
                name="State Cricket Association",
                department_id=dept.id,
                admin_id=fed_admin.id
            )
            db.add(fed)
            db.commit()
            db.refresh(fed)
            
            # Link Federation Admin to Federation
            fed_admin.federation_id = fed.id
            db.commit()
            print("State Cricket Association Federation created.")
        else:
            print("Federation already exists.")

        # Seed other roles
        players = [
            ("player1@sports.com", "Virat Kohli"),
            ("player2@sports.com", "Rohit Sharma"),
            ("player3@sports.com", "Jasprit Bumrah"),
            ("player4@sports.com", "KL Rahul"),
        ]
        for email, name in players:
            p = db.query(User).filter(User.email == email).first()
            if not p:
                p = User(
                    email=email,
                    hashed_password=security.get_password_hash("password123"),
                    full_name=name,
                    role="player",
                    is_approved=True
                )
                db.add(p)
                print(f"Player created: {email}")

        # Coach
        c = db.query(User).filter(User.role == "coach").first()
        if not c:
            c = User(
                email="coach@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="Rahul Dravid",
                role="coach",
                is_approved=True
            )
            db.add(c)
            print("Coach created: coach@sports.com")

        # Sponsor
        s = db.query(User).filter(User.role == "sponsor").first()
        if not s:
            s = User(
                email="sponsor@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="Adidas Sponsor",
                role="sponsor",
                is_approved=True
            )
            db.add(s)
            print("Sponsor created: sponsor@sports.com")

        # Scorer
        sc = db.query(User).filter(User.role == "scorer").first()
        if not sc:
            sc = User(
                email="scorer@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="Official Scorer Umpire",
                role="scorer",
                is_approved=True
            )
            db.add(sc)
            print("Scorer created: scorer@sports.com")

        db.commit()
        print("Database seeding completed successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
