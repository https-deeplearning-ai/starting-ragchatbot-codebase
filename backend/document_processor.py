import os
import re
from typing import List, Tuple

from models import Course, CourseChunk, Lesson


class DocumentProcessor:
    """Processes course documents and extracts structured information"""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def read_file(self, file_path: str) -> str:
        """Read content from file with UTF-8 encoding"""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with error handling
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                return file.read()

    def chunk_text(self, text: str) -> List[str]:
        """Split text into sentence-based chunks with overlap using config settings"""

        # Clean up the text
        text = re.sub(r"\s+", " ", text.strip())  # Normalize whitespace

        # Better sentence splitting that handles abbreviations
        # This regex looks for periods followed by whitespace and capital letters
        # but ignores common abbreviations
        sentence_endings = re.compile(
            r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+(?=[A-Z])"
        )
        sentences = sentence_endings.split(text)

        # Clean sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        i = 0

        while i < len(sentences):
            current_chunk = []
            current_size = 0

            # Build chunk starting from sentence i
            for j in range(i, len(sentences)):
                sentence = sentences[j]

                # Calculate size with space
                space_size = 1 if current_chunk else 0
                total_addition = len(sentence) + space_size

                # Check if adding this sentence would exceed chunk size
                if current_size + total_addition > self.chunk_size and current_chunk:
                    break

                current_chunk.append(sentence)
                current_size += total_addition

            # Add chunk if we have content
            if current_chunk:
                chunks.append(" ".join(current_chunk))

                # Calculate overlap for next chunk
                if hasattr(self, "chunk_overlap") and self.chunk_overlap > 0:
                    # Find how many sentences to overlap
                    overlap_size = 0
                    overlap_sentences = 0

                    # Count backwards from end of current chunk
                    for k in range(len(current_chunk) - 1, -1, -1):
                        sentence_len = len(current_chunk[k]) + (
                            1 if k < len(current_chunk) - 1 else 0
                        )
                        if overlap_size + sentence_len <= self.chunk_overlap:
                            overlap_size += sentence_len
                            overlap_sentences += 1
                        else:
                            break

                    # Move start position considering overlap
                    next_start = i + len(current_chunk) - overlap_sentences
                    i = max(next_start, i + 1)  # Ensure we make progress
                else:
                    # No overlap - move to next sentence after current chunk
                    i += len(current_chunk)
            else:
                # No sentences fit, move to next
                i += 1

        return chunks

    def process_course_document(
        self, file_path: str
    ) -> Tuple[Course, List[CourseChunk]]:
        """
        Process a course document with expected format:
        Line 1: Course Title: [title]
        Line 2: Course Link: [url]
        Line 3: Course Instructor: [instructor]
        Following lines: Lesson markers and content
        """
        content = self.read_file(file_path)
        filename = os.path.basename(file_path)

        lines = content.strip().split("\n")

        # Extract course metadata from first three lines
        course_title = filename  # Default fallback
        course_link = None
        instructor_name = "Unknown"

        # Parse course title from first line
        if len(lines) >= 1 and lines[0].strip():
            title_match = re.match(
                r"^Course Title:\s*(.+)$", lines[0].strip(), re.IGNORECASE
            )
            if title_match:
                course_title = title_match.group(1).strip()
            else:
                course_title = lines[0].strip()

        # Parse remaining lines for course metadata
        for i in range(1, min(len(lines), 4)):  # Check first 4 lines for metadata
            line = lines[i].strip()
            if not line:
                continue

            # Try to match course link
            link_match = re.match(r"^Course Link:\s*(.+)$", line, re.IGNORECASE)
            if link_match:
                course_link = link_match.group(1).strip()
                continue

            # Try to match instructor
            instructor_match = re.match(
                r"^Course Instructor:\s*(.+)$", line, re.IGNORECASE
            )
            if instructor_match:
                instructor_name = instructor_match.group(1).strip()
                continue

        # Create course object with title as ID
        course = Course(
            title=course_title,
            course_link=course_link,
            instructor=instructor_name if instructor_name != "Unknown" else None,
        )

        # Process lessons and create chunks
        course_chunks = []
        current_lesson = None
        lesson_title = None
        lesson_link = None
        lesson_content = []
        chunk_counter = 0

        # Start processing from line 4 (after metadata)
        start_index = 3
        if len(lines) > 3 and not lines[3].strip():
            start_index = 4  # Skip empty line after instructor

        i = start_index
        while i < len(lines):
            line = lines[i]

            # Check for lesson markers (e.g., "Lesson 0: Introduction")
            lesson_match = re.match(
                r"^Lesson\s+(\d+):\s*(.+)$", line.strip(), re.IGNORECASE
            )

            if lesson_match:
                # Process previous lesson if it exists
                if current_lesson is not None and lesson_content:
                    lesson_text = "\n".join(lesson_content).strip()
                    if lesson_text:
                        # Add lesson to course
                        lesson = Lesson(
                            lesson_number=current_lesson,
                            title=lesson_title,
                            lesson_link=lesson_link,
                        )
                        course.lessons.append(lesson)

                        # Create chunks for this lesson
                        chunks = self.chunk_text(lesson_text)
                        for idx, chunk in enumerate(chunks):
                            # For the first chunk of each lesson, add lesson context
                            if idx == 0:
                                chunk_with_context = (
                                    f"Lesson {current_lesson} content: {chunk}"
                                )
                            else:
                                chunk_with_context = chunk

                            course_chunk = CourseChunk(
                                content=chunk_with_context,
                                course_title=course.title,
                                lesson_number=current_lesson,
                                chunk_index=chunk_counter,
                            )
                            course_chunks.append(course_chunk)
                            chunk_counter += 1

                # Start new lesson
                current_lesson = int(lesson_match.group(1))
                lesson_title = lesson_match.group(2).strip()
                lesson_link = None

                # Check if next line is a lesson link
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    link_match = re.match(
                        r"^Lesson Link:\s*(.+)$", next_line, re.IGNORECASE
                    )
                    if link_match:
                        lesson_link = link_match.group(1).strip()
                        i += 1  # Skip the link line so it's not added to content

                lesson_content = []
            else:
                # Add line to current lesson content
                lesson_content.append(line)

            i += 1

        # Process the last lesson
        if current_lesson is not None and lesson_content:
            lesson_text = "\n".join(lesson_content).strip()
            if lesson_text:
                lesson = Lesson(
                    lesson_number=current_lesson,
                    title=lesson_title,
                    lesson_link=lesson_link,
                )
                course.lessons.append(lesson)

                chunks = self.chunk_text(lesson_text)
                for idx, chunk in enumerate(chunks):
                    # For any chunk of each lesson, add lesson context & course title

                    chunk_with_context = f"Course {course_title} Lesson {current_lesson} content: {chunk}"

                    course_chunk = CourseChunk(
                        content=chunk_with_context,
                        course_title=course.title,
                        lesson_number=current_lesson,
                        chunk_index=chunk_counter,
                    )
                    course_chunks.append(course_chunk)
                    chunk_counter += 1

        # If no lessons found, treat entire content as one document
        if not course_chunks and len(lines) > 2:
            remaining_content = "\n".join(lines[start_index:]).strip()
            if remaining_content:
                chunks = self.chunk_text(remaining_content)
                for chunk in chunks:
                    course_chunk = CourseChunk(
                        content=chunk,
                        course_title=course.title,
                        chunk_index=chunk_counter,
                    )
                    course_chunks.append(course_chunk)
                    chunk_counter += 1

        return course, course_chunks
