import os
import json
import pathlib
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit
from PyQt5.QtCore import QObject, Qt, pyqtSignal
import sys
from pathlib import Path


class NoteWindow(QMainWindow):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.setWindowTitle(os.path.basename(filename))
        self.text_edit = QTextEdit(self)
        self.setCentralWidget(self.text_edit)
        self.load_note()
        self.load_position()

        # Fensterfarbe auf Schwarz setzen
        self.setStyleSheet("background-color: gray; color: white;")
        self.text_edit.setStyleSheet("background-color: gray; color: white;")

        # Signal zum automatischen Speichern der Notiz bei Änderungen
        self.text_edit.textChanged.connect(self.save_note)

    def closeEvent(self, event):
        self.save_position()
        event.accept()

    def moveEvent(self, event):
        self.save_position()

    def save_note(self):
        print("saved text")
        with open(self.filename, 'w') as f:
            f.write(self.text_edit.toPlainText())

    def load_note(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                self.text_edit.setPlainText(f.read())

    def save_position(self):
        print("saved pos")
        position = {
            'x': self.x(),
            'y': self.y(),
            'width': self.width(),
            'height': self.height()
        }
        pos_filename = os.path.join(pos_path, f"{os.path.basename(self.filename)}.pos")
        with open(pos_filename, 'w') as f:
            json.dump(position, f)
        print(f"Position gespeichert: {position}")  # Debugging-Ausgabe

    def load_position(self):
        pos_filename = os.path.join(pos_path, f"{os.path.basename(self.filename)}.pos")
        try:
            with open(pos_filename, 'r') as f:
                position = json.load(f)
                x = position.get('x', self.x())
                y = position.get('y', self.y())
                width = position.get('width', self.width())
                height = position.get('height', self.height())
                self.move(x, y)
                self.resize(width, height)
                print(f"Position geladen: x={x}, y={y}, width={width}, height={height}")
        except FileNotFoundError:
            print("Positionsdatei nicht gefunden. Verwende Standardwerte.")
            self.resize(400, 300)
        except json.JSONDecodeError:
            print("Fehler beim Dekodieren der JSON-Datei. Verwende Standardwerte.")
            self.move(0, 0)
            self.resize(400, 300)


class NotesHandler(FileSystemEventHandler, QObject):  # Inherit from QObject
    new_note_signal = pyqtSignal(str)  # Signal to emit when a new note is created

    def __init__(self, app, windows, directory):
        QObject.__init__(self)  # Initialize QObject
        super().__init__()  # Initialize FileSystemEventHandler
        self.app = app
        self.windows = windows
        self.directory = directory
        self.new_note_signal.connect(self.add_new_window)  # Connect the signal to the slot

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.md') and os.path.exists(event.src_path):
            print(f"Neue Datei entdeckt: {event.src_path}")
            self.new_note_signal.emit(event.src_path)

    def on_moved(self, event):
        if event.dest_path.endswith('.md'):
            print(f"Datei verschoben: {event.dest_path}")
            self.new_note_signal.emit(event.dest_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.md'):
            print(f"Datei gelöscht: {event.src_path}")
            self.close_note_window(event.src_path)
            print("pos file deleted")

    def close_note_window(self, file_path):
        for window in self.windows:
            if window.filename == file_path:  # Compare the filename
                window.close()  # Close the window
                self.windows.remove(window)  # Remove from the list
                print(f"Notizfenster geschlossen für: {file_path}")

                pos_filename = os.path.join(pos_path, f"{os.path.basename(file_path)}.pos")
                if os.path.exists(pos_filename):
                    try:
                        os.remove(pos_filename)
                        print(f"Zugehörige .pos-Datei gelöscht: {pos_filename}")
                        time.sleep(1)
                        if os.path.exists(pos_filename):
                            os.remove(pos_filename)
                            print(f"Zugehörige .pos-Datei gelöscht: {pos_filename}")
                    except:
                        print("failed delete pos file")
                else:
                    print(f"Keine zugehörige .pos-Datei gefunden: {pos_filename}")
                break

    def add_new_window(self, file_path):
        if not os.path.exists(file_path):
            print(f"Datei nicht gefunden: {file_path}")
            return

        # Kurze Verzögerung, um sicherzustellen, dass die Datei vollständig kopiert wurde
        time.sleep(0.5)

        print(f"Erstelle neues Fenster für Datei: {file_path}")
        note_window = NoteWindow(file_path)
        note_window.show()
        self.windows.append(note_window)


if __name__ == "__main__":
    pos_path = Path(__file__).parent.resolve() / 'Pos'
    if not os.path.exists(pos_path):
        os.makedirs(pos_path)

    notes_directory = "/home/unknown/Nextcloud/Notizen/Notizen Tom"

    app = QApplication(sys.argv)
    windows = []

    # Bestehende Dateien laden
    for filename in os.listdir(notes_directory):
        if filename.endswith('.md'):
            note_window = NoteWindow(os.path.join(notes_directory, filename))
            note_window.show()
            windows.append(note_window)

    # Verzeichnis überwachen
    observer = Observer()
    event_handler = NotesHandler(app, windows, notes_directory)
    observer.schedule(event_handler, notes_directory, recursive=False)
    observer.start()

    try:
        sys.exit(app.exec_())
    finally:
        observer.stop()
        observer.join()