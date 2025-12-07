# Teacher Print Feature - Term Selection Implementation

## Summary
Updated the teacher print report feature to allow easy selection of complete term reports (combining both Midterm and End_term exams).

## Changes Made

### 1. **prepare_print.html** - Added Term Quick Select
- Added a new "Quick Select by Term" card with three buttons (Term 1, Term 2, Term 3)
- When teacher clicks a term button, it automatically selects both Midterm and End_term exams for that term
- Teachers can still manually select individual exams if they prefer
- Simplified description: "Select the term or exams you want to include in the printout"

### 2. **print_selected.html** - Added Combined Report Header
- Detects when both Midterm and End_term are selected for the same term
- Displays a prominent "TERM X COMBINED REPORT" header when both exam types are present
- Header clearly shows "Showing both Midterm and End_term assessments"
- The combined statistics calculation automatically weights Midterm (40%) and End_term (60%)

## How It Works

### For Teachers:
1. Click "Print" on a pupil's profile
2. Choose to **either**:
   - Click "Term 1", "Term 2", or "Term 3" button to automatically select both exams
   - OR manually check individual exams from the list
3. Click "Print selected"
4. The report displays:
   - A header showing it's a TERM X COMBINED REPORT (if both exams selected)
   - Individual Midterm scores and grades
   - Individual End_term scores and grades
   - Combined statistics (weighted: Midterm 40%, End_term 60%)
   - Rankings by stream and class position

### Data Requirements:
- Midterm exam must have marks for the pupil
- End_term exam must have marks for the pupil
- Both will be included in the combined report

## Database Structure
The system expects:
- Term 1: Exam ID 25 (Midterm) + Exam ID 26 (End Term) ✓ (Already populated with 8,400 marks each)
- Term 2: Exam ID 27 (Midterm) + Exam ID 28 (End Term)
- Term 3: Exam ID 29 (Midterm) + Exam ID 30 (End Term)

## Example Flow
```
Teacher clicks "Print" for pupil Nairobi Kinyanjui
  ↓
System shows available exams for that pupil
  ↓
Teacher clicks "Term 1" button
  ↓
Both Midterm (ID 25) and End Term (ID 26) are auto-selected
  ↓
Teacher clicks "Print selected"
  ↓
Report displays with "TERM 1 COMBINED REPORT" header
  ↓
Shows both Midterm and End_term results combined
  ↓
Teacher can download PDF or print directly
```

## Testing
Verified that:
- Pupil data exists (2,100 pupils across all classes/streams)
- Term 1 Midterm marks: 8,400 marks ✓
- Term 1 End_term marks: 8,400 marks ✓
- Exams properly associated with pupils ✓
- Quick select functionality ready to test in UI ✓
