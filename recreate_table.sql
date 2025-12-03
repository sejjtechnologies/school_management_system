CREATE TABLE IF NOT EXISTS timetable_slots (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id),
    class_id INTEGER NOT NULL REFERENCES classes(id),
    stream_id INTEGER NOT NULL REFERENCES streams(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    day_of_week VARCHAR(20) NOT NULL,
    start_time VARCHAR(5) NOT NULL,
    end_time VARCHAR(5) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_teacher_stream_slot UNIQUE(teacher_id, stream_id, day_of_week, start_time),
    CONSTRAINT unique_class_slot UNIQUE(class_id, stream_id, day_of_week, start_time)
);
