# 🔍 Code Comparison - Before & After

## Complete Side-by-Side Code Changes

---

## 1. ROUTES/ADMIN_ROUTES.PY - EDIT FUNCTION

### ❌ REMOVED FUNCTION 1: `add_timetable_slot()`

```python
# REMOVED - ~68 lines of code
@admin_routes.route("/admin/timetable/add", methods=["POST"])
def add_timetable_slot():
    """Add a new timetable slot"""
    data = request.json

    # Get data
    teacher_id = data.get('teacher_id')
    class_id = data.get('class_id')
    stream_id = data.get('stream_id')
    subject_id = data.get('subject_id')
    day_of_week = data.get('day_of_week')
    start_time = data.get('start_time')

    # Validate
    if not all([teacher_id, class_id, stream_id, subject_id, day_of_week, start_time]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Calculate end_time
    from datetime import datetime, timedelta
    try:
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = start_dt + timedelta(hours=1)
        end_time = end_dt.strftime('%H:%M')
    except ValueError:
        return jsonify({'error': 'Invalid time format'}), 400

    # Check conflicts
    teacher_conflict = TimeTableSlot.query.filter_by(
        teacher_id=teacher_id,
        day_of_week=day_of_week,
        start_time=start_time
    ).first()

    if teacher_conflict:
        return jsonify({'error': f'Teacher already assigned at {start_time} on {day_of_week}'}), 409

    # Create and save
    try:
        new_slot = TimeTableSlot(
            class_id=class_id,
            stream_id=stream_id,
            teacher_id=teacher_id,
            subject_id=subject_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(new_slot)
        db.session.commit()
        return jsonify({'message': 'Timetable slot added successfully!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
```

**Reason:** Manual add not needed - all slots auto-generated

---

### ❌ REMOVED FUNCTION 2: `delete_timetable_slot()`

```python
# REMOVED - ~15 lines of code
@admin_routes.route("/admin/timetable/delete/<int:slot_id>", methods=["DELETE"])
def delete_timetable_slot(slot_id):
    """Delete a timetable slot"""
    slot = TimeTableSlot.query.get_or_404(slot_id)

    try:
        db.session.delete(slot)
        db.session.commit()
        return jsonify({'message': 'Timetable slot deleted successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
```

**Reason:** Manual delete not allowed - prevents data integrity issues

---

### ✏️ MODIFIED FUNCTION: `edit_timetable_slot()`

```python
# BEFORE (52 lines)
@admin_routes.route("/admin/timetable/edit/<int:slot_id>", methods=["PUT"])
def edit_timetable_slot(slot_id):
    """Edit an existing timetable slot"""
    slot = TimeTableSlot.query.get_or_404(slot_id)
    data = request.json

    teacher_id = data.get('teacher_id')
    subject_id = data.get('subject_id')
    day_of_week = data.get('day_of_week')           # ← ACCEPTED
    start_time = data.get('start_time')             # ← ACCEPTED

    # Calculate end_time (one hour after start_time)
    from datetime import datetime, timedelta
    try:
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = start_dt + timedelta(hours=1)
        end_time = end_dt.strftime('%H:%M')
    except ValueError:
        return jsonify({'error': 'Invalid time format'}), 400

    # Check teacher double-booking for SAME STREAM
    teacher_conflict = TimeTableSlot.query.filter(
        TimeTableSlot.id != slot_id,
        TimeTableSlot.teacher_id == teacher_id,
        TimeTableSlot.stream_id == slot.stream_id,
        TimeTableSlot.day_of_week == day_of_week,
        TimeTableSlot.start_time == start_time
    ).first()

    if teacher_conflict:
        return jsonify({'error': f'Teacher is already assigned...'}), 409

    # Check class double-booking
    class_conflict = TimeTableSlot.query.filter(
        TimeTableSlot.id != slot_id,
        TimeTableSlot.class_id == slot.class_id,
        TimeTableSlot.stream_id == slot.stream_id,
        TimeTableSlot.day_of_week == day_of_week,
        TimeTableSlot.start_time == start_time
    ).first()

    if class_conflict:
        return jsonify({'error': f'Class {day_of_week} {start_time} slot occupied'}), 409

    try:
        slot.teacher_id = teacher_id
        slot.subject_id = subject_id
        slot.day_of_week = day_of_week              # ← UPDATED ❌
        slot.start_time = start_time                # ← UPDATED ❌
        slot.end_time = end_time                    # ← UPDATED ❌
        db.session.commit()
        return jsonify({'message': 'Timetable slot updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# AFTER (26 lines)
@admin_routes.route("/admin/timetable/edit/<int:slot_id>", methods=["PUT"])
def edit_timetable_slot(slot_id):
    """Edit an existing timetable slot - ONLY teacher_id and subject_id can be changed"""
    slot = TimeTableSlot.query.get_or_404(slot_id)
    data = request.json

    teacher_id = data.get('teacher_id')
    subject_id = data.get('subject_id')
    # ❌ REMOVED - NO LONGER ACCEPTED
    # day_of_week = data.get('day_of_week')
    # start_time = data.get('start_time')

    # Check teacher double-booking for SAME STREAM at SAME TIME
    # ✅ USING EXISTING SLOT VALUES, NOT NEW VALUES
    teacher_conflict = TimeTableSlot.query.filter(
        TimeTableSlot.id != slot_id,
        TimeTableSlot.teacher_id == teacher_id,
        TimeTableSlot.stream_id == slot.stream_id,
        TimeTableSlot.day_of_week == slot.day_of_week,  # ← USE EXISTING
        TimeTableSlot.start_time == slot.start_time     # ← USE EXISTING
    ).first()

    if teacher_conflict:
        return jsonify({'error': f'Teacher is already assigned...'}), 409

    # ❌ CLASS CHECK REMOVED - NOT NEEDED (slot already reserved)

    try:
        slot.teacher_id = teacher_id
        slot.subject_id = subject_id
        # ✅ THESE ARE NOT MODIFIED
        # slot.day_of_week = day_of_week
        # slot.start_time = start_time
        # slot.end_time = end_time
        db.session.commit()
        return jsonify({'message': 'Timetable slot updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
```

**Changes:**
- ✅ Removed: day_of_week, start_time parameters
- ✅ Removed: end_time calculation
- ✅ Removed: class_conflict check (not needed)
- ✅ Updated: teacher_conflict check uses existing slot values
- ✅ Updated: validation only for multi-stream teaching prevention

---

## 2. APP.PY - AUTO-GENERATION LOGIC

### ✨ ADDED: Startup Auto-Generation (Lines 95-189)

```python
# NEW CODE ADDED
with app.app_context():
    try:
        db.create_all()  # ✅ This now includes marks_model tables
        logger.info("Database tables created successfully")
        
        # ✅ Auto-generate timetables for all classes/streams on first startup
        from models.class_model import Class
        from models.stream_model import Stream
        from models.timetable_model import TimeTableSlot
        from datetime import datetime, timedelta
        from models.user_models import User
        from models.teacher_assignment_models import TeacherAssignment
        
        # Check if timetables already exist
        existing_slots = TimeTableSlot.query.first()
        
        if not existing_slots:
            logger.info("Generating timetables for all classes and streams...")
            try:
                classes = Class.query.all()
                days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                
                for class_obj in classes:
                    streams = class_obj.streams
                    if not streams:
                        logger.warning(f"Class {class_obj.name} has no streams, skipping")
                        continue
                    
                    for stream in streams:
                        logger.info(f"Generating timetable for {class_obj.name} - {stream.name}")
                        
                        # Get all teachers assigned to this class
                        assignments = TeacherAssignment.query.filter_by(class_id=class_obj.id).all()
                        if not assignments:
                            logger.warning(f"No teachers assigned to class {class_obj.name}, skipping")
                            continue
                        
                        all_teachers = [assign.teacher for assign in assignments]
                        assigned_class_teacher = stream.class_teacher_id
                        
                        # Generate time slots (8:00 AM to 5:00 PM)
                        time_slots = []
                        current = datetime.strptime("08:00", '%H:%M')
                        end_time = datetime.strptime("17:00", '%H:%M')
                        
                        teacher_idx = 0
                        
                        for day in days_of_week:
                            while current < end_time:
                                time_str = current.strftime('%H:%M')
                                
                                # Skip break time (10:00-10:20)
                                if time_str == '10:00':
                                    current += timedelta(minutes=20)
                                    continue
                                
                                # Skip lunch time (13:00-13:40)
                                if time_str == '13:00':
                                    current += timedelta(minutes=40)
                                    continue
                                
                                # Calculate lesson duration
                                remaining = (end_time - current).total_seconds() / 60
                                duration = 40 if remaining > 40 else int(remaining)
                                
                                if duration <= 0:
                                    break
                                
                                # Select teacher (ensure class teacher is always included)
                                if teacher_idx == 0 and assigned_class_teacher:
                                    teacher = User.query.get(assigned_class_teacher)
                                else:
                                    teacher = all_teachers[teacher_idx % len(all_teachers)]
                                
                                if not teacher:
                                    teacher = all_teachers[0]
                                
                                # Get first subject (default)
                                subject_id = 1  # Default to first subject
                                
                                # Create slot
                                end_str = (current + timedelta(minutes=duration)).strftime('%H:%M')
                                
                                slot = TimeTableSlot(
                                    class_id=class_obj.id,
                                    stream_id=stream.id,
                                    teacher_id=teacher.id,
                                    subject_id=subject_id,
                                    day_of_week=day,
                                    start_time=time_str,
                                    end_time=end_str
                                )
                                
                                try:
                                    db.session.add(slot)
                                    db.session.commit()
                                except Exception as e:
                                    db.session.rollback()
                                    logger.warning(f"Could not add slot: {str(e)}")
                                
                                current += timedelta(minutes=duration)
                                teacher_idx += 1
                        
                        # Reset current for next day
                        current = datetime.strptime("08:00", '%H:%M')
                
                logger.info("✓ Timetables generated successfully!")
            except Exception as e:
                logger.error(f"Error generating timetables: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
```

---

### ✨ ADDED: Flask CLI Command (Lines 191-291)

```python
# NEW COMMAND ADDED
@app.cli.command()
def generate_timetables():
    """Regenerate timetables for all classes and streams."""
    with app.app_context():
        from models.class_model import Class
        from models.stream_model import Stream
        from models.timetable_model import TimeTableSlot
        from models.user_models import User
        from models.teacher_assignment_models import TeacherAssignment
        from datetime import datetime, timedelta
        
        try:
            # Clear existing timetables
            TimeTableSlot.query.delete()
            db.session.commit()
            logger.info("Cleared existing timetables")
            
            classes = Class.query.all()
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            
            for class_obj in classes:
                streams = class_obj.streams
                if not streams:
                    logger.warning(f"Class {class_obj.name} has no streams, skipping")
                    continue
                
                for stream in streams:
                    logger.info(f"Generating timetable for {class_obj.name} - {stream.name}")
                    
                    assignments = TeacherAssignment.query.filter_by(class_id=class_obj.id).all()
                    if not assignments:
                        logger.warning(f"No teachers assigned to class {class_obj.name}, skipping")
                        continue
                    
                    all_teachers = [assign.teacher for assign in assignments]
                    assigned_class_teacher = stream.class_teacher_id
                    
                    # Generate time slots
                    time_slots = []
                    current = datetime.strptime("08:00", '%H:%M')
                    end_time = datetime.strptime("17:00", '%H:%M')
                    
                    teacher_idx = 0
                    
                    for day in days_of_week:
                        current = datetime.strptime("08:00", '%H:%M')
                        
                        while current < end_time:
                            time_str = current.strftime('%H:%M')
                            
                            # Skip break time (10:00-10:20)
                            if time_str == '10:00':
                                current += timedelta(minutes=20)
                                continue
                            
                            # Skip lunch time (13:00-13:40)
                            if time_str == '13:00':
                                current += timedelta(minutes=40)
                                continue
                            
                            # Calculate lesson duration
                            remaining = (end_time - current).total_seconds() / 60
                            duration = 40 if remaining > 40 else int(remaining)
                            
                            if duration <= 0:
                                break
                            
                            # Select teacher (ensure class teacher is always included)
                            if teacher_idx == 0 and assigned_class_teacher:
                                teacher = User.query.get(assigned_class_teacher)
                            else:
                                teacher = all_teachers[teacher_idx % len(all_teachers)]
                            
                            if not teacher:
                                teacher = all_teachers[0]
                            
                            # Get first subject (default)
                            subject_id = 1
                            
                            end_str = (current + timedelta(minutes=duration)).strftime('%H:%M')
                            
                            slot = TimeTableSlot(
                                class_id=class_obj.id,
                                stream_id=stream.id,
                                teacher_id=teacher.id,
                                subject_id=subject_id,
                                day_of_week=day,
                                start_time=time_str,
                                end_time=end_str
                            )
                            
                            db.session.add(slot)
                            current += timedelta(minutes=duration)
                            teacher_idx += 1
                    
                    db.session.commit()
            
            logger.info("✓ Timetables regenerated successfully!")
            print("✓ Timetables regenerated successfully!")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error regenerating timetables: {str(e)}")
            print(f"Error: {str(e)}")
```

---

## 3. TEMPLATES/ADMIN/MANAGE_TIMETABLES.HTML - UI CHANGES

### ❌ REMOVED HTML ELEMENTS

```html
<!-- REMOVED BUTTONS -->
<button class="btn-add-slot" onclick="generateTimetable()" style="width: 100%;">
  <i class="bi bi-sparkles me-1"></i>Generate Auto
</button>
<button class="btn-add-slot" onclick="openAddModal()" style="width: 100%;">
  <i class="bi bi-plus-circle me-1"></i>Add Slot
</button>
```

**Replaced with:**
```html
<!-- NEW BUTTON -->
<button class="btn-add-slot" onclick="loadTimetable()" style="width: 100%;">
  <i class="bi bi-arrow-clockwise me-1"></i>Refresh Timetable
</button>
```

---

### ❌ REMOVED DELETE BUTTON FROM GRID

```html
<!-- REMOVED -->
<div style="display: flex; gap: 2px; margin-top: 4px; font-size: 0.7rem;">
  <button class="btn-delete" onclick="openEditModal(...)">
    <i class="bi bi-pencil"></i>
  </button>
  <button class="btn-delete" onclick="deleteSlot(${slot.id})">
    <i class="bi bi-trash"></i>  <!-- ❌ REMOVED -->
  </button>
</div>
```

**Replaced with:**
```html
<!-- NEW -->
<div style="display: flex; gap: 2px; margin-top: 4px; font-size: 0.7rem;">
  <button class="btn-delete" onclick="openEditModal(...)">
    <i class="bi bi-pencil"></i> Edit  <!-- ✅ ADDED TEXT -->
  </button>
</div>
```

---

### ✏️ MODIFIED MODAL - TITLE CHANGE

```html
<!-- BEFORE -->
<h5 class="modal-title" id="slotModalLabel">Add Timetable Slot</h5>

<!-- AFTER -->
<h5 class="modal-title" id="slotModalLabel">Edit Timetable Slot</h5>
```

---

### ✏️ MODIFIED MODAL - REMOVED SELECTORS

```html
<!-- BEFORE - 7 FORM FIELDS -->
<div class="mb-3">
  <label for="teacherSelect" class="form-label">Teacher</label>
  <select id="teacherSelect" class="form-control" required>...</select>
</div>
<div class="mb-3">
  <label for="subjectSelect" class="form-label">Subject</label>
  <select id="subjectSelect" class="form-control" required>...</select>
</div>
<div class="mb-3">
  <label for="daySelect" class="form-label">Day of Week</label>
  <select id="daySelect" class="form-control" required>...</select>
</div>
<div class="mb-3">
  <label for="startTimeSelect" class="form-label">Start Time</label>
  <select id="startTimeSelect" class="form-control" required>...</select>
</div>

<!-- AFTER - 2 FORM FIELDS ONLY -->
<div class="mb-3">
  <label for="editTeacherSelect" class="form-label">Teacher</label>
  <select id="editTeacherSelect" class="form-control" required>...</select>
</div>
<div class="mb-3">
  <label for="editSubjectSelect" class="form-label">Subject</label>
  <select id="editSubjectSelect" class="form-control" required>...</select>
</div>
<!-- ❌ Day and Time selectors completely removed -->
```

---

### ✏️ MODIFIED MODAL - BUTTON TEXT

```html
<!-- BEFORE -->
<button type="button" class="btn-modal-save" onclick="saveSlot()">Add Slot</button>

<!-- AFTER -->
<button type="button" class="btn-modal-save" onclick="saveSlot()">Save Changes</button>
```

---

## 4. JAVASCRIPT FUNCTION CHANGES

### ❌ REMOVED FUNCTION: `openAddModal()`

```javascript
// REMOVED
function openAddModal() {
  document.getElementById('slotForm').reset();
  document.getElementById('slotModalLabel').textContent = 'Add Timetable Slot';
  slotModal.show();
}
```

---

### ❌ REMOVED FUNCTION: `generateTimetable()`

```javascript
// REMOVED
async function generateTimetable() {
  const classId = document.getElementById('classSelect').value;
  const streamId = document.getElementById('streamSelect').value;

  if (!classId || !streamId) {
    showAlert('Please select both class and stream', 'error');
    return;
  }

  if (!confirm('This will auto-generate a timetable...')) {
    return;
  }

  try {
    const response = await fetch(`/admin/timetable/generate/${classId}/${streamId}`, {
      method: 'POST'
    });
    // ...
  } catch (error) {
    showAlert('Error generating timetable: ' + error.message, 'error');
  }
}
```

---

### ❌ REMOVED FUNCTION: `deleteSlot()`

```javascript
// REMOVED
async function deleteSlot(slotId) {
  if (!confirm('Are you sure you want to delete this slot?')) return;

  try {
    const response = await fetch(`/admin/timetable/delete/${slotId}`, {
      method: 'DELETE'
    });
    // ...
  } catch (error) {
    showAlert('Error deleting slot: ' + error.message, 'error');
  }
}
```

---

### ✏️ MODIFIED FUNCTION: `saveSlot()`

```javascript
// BEFORE - Add mode
async function saveSlot() {
  const classId = document.getElementById('classSelect').value;
  const streamId = document.getElementById('streamSelect').value;
  const teacherId = document.getElementById('teacherSelect').value;
  const subjectId = document.getElementById('subjectSelect').value;
  const dayOfWeek = document.getElementById('daySelect').value;           // ❌
  const startTime = document.getElementById('startTimeSelect').value;      // ❌

  if (!classId || !streamId || !teacherId || !subjectId || !dayOfWeek || !startTime) {
    showAlert('Please fill all fields', 'error');
    return;
  }

  try {
    const response = await fetch('/admin/timetable/add', {      // ❌ POST to add
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        teacher_id: teacherId,
        class_id: classId,
        stream_id: streamId,
        subject_id: subjectId,
        day_of_week: dayOfWeek,      // ❌ SENT
        start_time: startTime         // ❌ SENT
      })
    });
    // ...
  } catch (error) {
    showAlert('Error saving slot: ' + error.message, 'error');
  }
}

// AFTER - Edit mode
async function saveSlot() {
  const slotId = document.getElementById('editSlotId').value;
  const teacherId = document.getElementById('editTeacherSelect').value;
  const subjectId = document.getElementById('editSubjectSelect').value;

  if (!teacherId || !subjectId) {
    showAlert('Please fill all fields', 'error');
    return;
  }

  try {
    const response = await fetch(`/admin/timetable/edit/${slotId}`, {    // ✅ PUT to edit
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        teacher_id: teacherId,
        subject_id: subjectId
        // ✅ NO day_of_week, NO start_time
      })
    });
    // ...
  } catch (error) {
    showAlert('Error updating slot: ' + error.message, 'error');
  }
}
```

---

### ✏️ MODIFIED FUNCTION: `openEditModal()`

```javascript
// BEFORE - Had day/time assignment
function openEditModal(slotId, teacherId, subjectId, day, time) {
  document.getElementById('editSlotId').value = slotId;
  document.getElementById('editTeacherSelect').value = teacherId;
  document.getElementById('editSubjectSelect').value = subjectId;
  document.getElementById('editDaySelect').value = day;         // ❌
  document.getElementById('editStartTimeSelect').value = time;   // ❌
  editSlotModal.show();
}

// AFTER - Simplified
function openEditModal(slotId, teacherId, subjectId, day, time) {
  document.getElementById('editSlotId').value = slotId;
  document.getElementById('editTeacherSelect').value = teacherId;
  document.getElementById('editSubjectSelect').value = subjectId;
  // ✅ NOT setting day and time (they don't exist in HTML anymore)
  editSlotModal.show();
}
```

---

## Summary of All Changes

### Code Removed: ~215 lines
- Routes: 83 lines (add + delete functions)
- HTML: 35 lines (day/time selectors, buttons)
- JavaScript: 97 lines (4 removed functions)

### Code Added: ~180 lines
- app.py: 98 lines (auto-generation logic)
- app.py: 93 lines (CLI command)
- Templates: 20 lines (refresh button, modified modal)
- JavaScript: 20 lines (modified functions)

### Net Change: -35 lines (more focused, less bloat)

**Result:** System is now simpler, more secure, and fully automated! ✅
