#!/usr/bin/env python
"""Check current timetable state and real teachers."""

try:
    from app import app, db
    from models.timetable_model import TimeTableSlot
    from models.user_models import User, Role
    
    app.app_context().push()
    
    print("Connected to database\n")
    
    # Check slots
    slot_count = db.session.query(TimeTableSlot).count()
    print(f"Total timetable slots: {slot_count}")
    
    # Check unique teachers in slots
    teacher_ids_in_slots = db.session.query(TimeTableSlot.teacher_id).distinct().all()
    print(f"Unique teacher IDs in slots: {[t[0] for t in teacher_ids_in_slots]}")
    
    # Check real teachers
    real_teachers = User.query.join(Role).filter(
        Role.role_name.ilike('teacher'),
        ~User.email.ilike('%@example.local'),
        ~User.first_name.ilike('teacher%')
    ).all()
    
    print(f"\nReal teachers ({len(real_teachers)}):")
    for t in real_teachers:
        print(f"  ID {t.id}: {t.first_name} {t.last_name} ({t.email})")
    
    # Check auto-created teachers
    auto_teachers = User.query.join(Role).filter(
        Role.role_name.ilike('teacher'),
        (User.email.ilike('%@example.local') | User.first_name.ilike('teacher%'))
    ).all()
    
    print(f"\nAuto-created teachers ({len(auto_teachers)}):")
    for t in auto_teachers:
        print(f"  ID {t.id}: {t.first_name} {t.last_name} ({t.email})")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
