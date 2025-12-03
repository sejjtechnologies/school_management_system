# Timetable Management System - Complete Guide

## Overview
The timetable system is now **fully automated**. The system:
- **Auto-generates** complete timetables for all classes and streams on app startup
- **Stores** timetables in the database
- Allows users to **VIEW** timetables from the database
- Allows users to **EDIT** only teacher and subject assignments (time slots are locked)
- **Prevents** manual add/delete operations to maintain data integrity

## How It Works

### 1. **Auto-Generation on App Startup**
When the application starts, it automatically:
1. Creates database tables (if missing)
2. Checks if timetables already exist
3. If NO timetables exist, it generates them for all classes and streams
4. Each stream gets:
   - 40-minute lessons throughout the day
   - Time range: 8:00 AM to 5:00 PM
   - 20-minute break at 10:00 AM
   - 40-minute lunch at 1:00 PM
   - Class teacher always included in the schedule
   - All available teachers distributed round-robin across time slots

### 2. **Access the Timetable**
**Path:** `/admin/timetable` (Admin Dashboard)

**Steps:**
1. Select a Class from dropdown
2. Select a Stream from dropdown
3. Click "Load Timetable" button
4. Timetable grid displays all 6 days and 15 time slots

### 3. **Edit a Slot**
**What you CAN edit:**
- ✅ Teacher assignment
- ✅ Subject assignment

**What you CANNOT edit (locked):**
- ❌ Day of Week
- ❌ Time slot
- ❌ Lesson duration

**Steps to edit:**
1. Click the "Edit" button on any slot
2. Modal opens with Teacher and Subject selectors only
3. Change Teacher and/or Subject as needed
4. Click "Save Changes"
5. Changes are saved to the database immediately

### 4. **Viewing Information**
The interface shows:
- **Timetable Grid:** All days (Mon-Sat) × Time slots
- **Time Format:** 12-hour AM/PM (e.g., "2:30 PM")
- **Special Markers:** Break and Lunch periods shown with icons
- **Assigned Teachers Info:** List of all teachers assigned to the class

## Technical Details

### Database Structure
**TimeTableSlot table columns:**
- `id` - Primary key
- `class_id` - Foreign key to Class
- `stream_id` - Foreign key to Stream  
- `teacher_id` - Foreign key to User (Teacher)
- `subject_id` - Foreign key to Subject
- `day_of_week` - Monday through Saturday
- `start_time` - Start time (HH:MM format)
- `end_time` - End time (HH:MM format)
- `created_at` - Timestamp

**Database Constraints:**
- **Unique constraint 1:** `(teacher_id, stream_id, day_of_week, start_time)`
  - Prevents same teacher teaching same stream at same time
  - **Allows** same teacher in different streams at same time (multi-stream teaching)
  
- **Unique constraint 2:** `(class_id, stream_id, day_of_week, start_time)`
  - Prevents double-booking a stream at same time slot

### Backend Changes

#### ✅ Routes Modified
- **`POST /admin/timetable/generate/:class_id/:stream_id`** - Removed (no longer exposed)
- **`POST /admin/timetable/add`** - Removed (manual add disabled)
- **`DELETE /admin/timetable/delete/:slot_id`** - Removed (manual delete disabled)
- **`PUT /admin/timetable/edit/:slot_id`** - Modified
  - Now accepts ONLY: `teacher_id`, `subject_id`
  - Validates teacher not already assigned to same stream at same time
  - Does NOT accept: `day_of_week`, `start_time`, `end_time`

#### ✅ Models
- `TimeTableSlot` model uses updated constraint for multi-stream teaching
- All relationships properly configured with backref

### Frontend Changes

#### ✅ Template (`manage_timetables.html`)
- **Removed buttons:**
  - "Generate Auto" button (replaced with "Refresh Timetable")
  - "Add Slot" button
  - Delete button from grid
  
- **Modified modal:**
  - Only shows Teacher and Subject selectors
  - Removed Day/Time selectors
  - Button text changed from "Add Slot" to "Save Changes"
  
- **Grid buttons:**
  - Only "Edit" button remains per slot

#### ✅ JavaScript Functions
- **Removed:** `openAddModal()`, `generateTimetable()`, `openAddModalForCell()`, `deleteSlot()`
- **Modified:** `saveSlot()` - Now only sends teacher_id and subject_id
- **Kept:** `openEditModal()`, `loadTimetable()`, `loadAssignedTeachers()`, `renderTimetable()`

## Regeneration Command

### For Administrators: Regenerate All Timetables
If you need to regenerate timetables (clear and recreate all), run:

```bash
# From project root
flask --app app.py generate-timetables
```

Or in Python environment:
```bash
export FLASK_APP=app.py
flask generate-timetables
```

**This command will:**
1. Delete all existing timetable slots from database
2. Regenerate for all classes and streams
3. Apply same logic as startup generation

## Example Lesson Schedule

**For P1 Stream A (Monday):**
```
8:00 AM  - 8:40 AM   → Teacher 1, Subject 1
8:40 AM  - 9:20 AM   → Teacher 2, Subject 2
9:20 AM  - 10:00 AM  → Teacher 3, Subject 3
10:00 AM - 10:20 AM  → ☕ 20 MIN BREAK
10:20 AM - 11:00 AM  → Teacher 1, Subject 1
11:00 AM - 11:40 AM  → Teacher 2, Subject 2
11:40 AM - 12:20 PM  → Teacher 3, Subject 3
12:20 PM - 1:00 PM   → Teacher 1, Subject 1
1:00 PM  - 1:40 PM   → 🍽️ 40 MIN LUNCH
1:40 PM  - 2:20 PM   → Teacher 2, Subject 2
2:20 PM  - 3:00 PM   → Teacher 3, Subject 3
3:00 PM  - 3:40 PM   → Teacher 1, Subject 1
3:40 PM  - 4:20 PM   → Teacher 2, Subject 2
4:20 PM  - 5:00 PM   → Teacher 3, Subject 3
```

## Important Notes

1. **First Run:** Timetables are generated automatically on first app startup
2. **Time Format:** All times stored in 24-hour format (HH:MM), displayed in 12-hour AM/PM
3. **Multi-stream Teaching:** A teacher CAN teach different subjects in different streams at the same time
4. **Class Teacher:** Always included in their assigned stream's schedule
5. **Database Persistence:** All changes are immediately saved to the database
6. **No Manual Scheduling:** To ensure consistency, users cannot manually add/delete slots

## Troubleshooting

### Timetable Not Loading
- Check if class and stream are selected
- Verify database connection is active
- Check browser console for errors

### Cannot Edit a Slot
- Ensure the new teacher is not already assigned to the same stream at that time
- Check that teacher has a role "Teacher" in the system
- Verify subject is valid in database

### Timetable Not Generated on Startup
- Check application logs for errors
- Verify teachers are assigned to classes
- Ensure database connection is working
- Run `flask generate-timetables` command manually

## Future Enhancements

Possible improvements:
- [ ] Custom lesson duration settings per stream
- [ ] Bulk teacher assignment for multiple streams
- [ ] Subject preferences per teacher
- [ ] Time slot preferences (avoid certain times)
- [ ] Conflict detection and resolution
- [ ] Timetable versioning/history
- [ ] Export timetable to PDF

---

**Last Updated:** $(date)
**System Version:** 1.0 - Auto-Generated Timetable System
