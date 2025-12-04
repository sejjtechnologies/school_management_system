import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app

with app.app_context():
    from models.class_model import Class
    from models.stream_model import Stream
    from models.user_models import User, Role
    from models.timetable_model import TimeTableSlot

    classes = Class.query.all()
    streams = Stream.query.all()
    teachers = User.query.join(Role).filter(Role.role_name=='teacher').all()
    out_lines = []
    out_lines.append(f"Classes ({len(classes)}): {[c.name for c in classes]}")
    out_lines.append(f"Streams ({len(streams)}): {[s.name for s in streams]}")
    out_lines.append(f"Teachers ({len(teachers)}): {[t.email for t in teachers]}\n")

    # Count timetable slots per class-stream
    slots = TimeTableSlot.query.all()
    counts = {}
    for s in slots:
        key = f"{s.class_id}-{s.stream_id}"
        counts[key] = counts.get(key, 0) + 1

    out_lines.append('Timetable slots per class-stream:')
    for k,v in counts.items():
        out_lines.append(f"  {k}: {v}")

    # Write to file for inspection
    out_path = os.path.join(os.path.dirname(__file__), '..', 'inspect_output.txt')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    print(f"Wrote inspection output to {out_path}")
