import os
import sys
import random
from pydub import AudioSegment
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QFormLayout, QPushButton, QLabel, QLineEdit, QFileDialog, \
    QProgressBar, QCheckBox, QHBoxLayout
from PyQt5.QtGui import QIntValidator, QIcon
from PyQt5.QtCore import Qt, pyqtSlot, QRunnable, QThreadPool, QThread

# Checks environment (pyinstaller package or IDE) and sets paths
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
    ffmpeg_path = os.path.join(base_path, "ffmpeg.exe")
    ffprobe_path = os.path.join(base_path, "ffprobe.exe")

    # Set converter path to ffmpeg
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffmpeg = ffmpeg_path
    AudioSegment.ffmpeg_options = {'creationflags': 0x08000000}
    AudioSegment.ffprobe = ffprobe_path
    AudioSegment.ffprobe_options = {'creationflags': 0x08000000}
else:
    base_path = os.path.dirname(__file__)


class WorkerSignals(QtCore.QObject):
    progressSignal = QtCore.pyqtSignal(int)
    finish = QtCore.pyqtSignal(str)
    freeze_x = QtCore.pyqtSignal()


class Worker(QRunnable):
    def __init__(self, shred_length, original_audio_locations, interlace, parent=None):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.shred_length = shred_length
        self.original_audio_locations = original_audio_locations
        self.shredded_parts = []
        self.parent = parent
        self.interlace = interlace

    @pyqtSlot()
    def run(self):

        songs_slices = []
        progress_p1 = 0

        if self.interlace:
            for original_audio_location in self.original_audio_locations:
                song = AudioSegment.from_file(original_audio_location)
                sliced_list = list(song[::int(self.shred_length)])
                random.shuffle(sliced_list)  # Shuffle the slices within each song
                songs_slices.append(sliced_list)
                progress_p1 = progress_p1 + 1
                self.signals.progressSignal.emit(int(progress_p1))

            # Interlace the songs
            song_count = len(songs_slices)
            min_length = min(len(slices) for slices in songs_slices)  # Get the minimum length

            for i in range(min_length):  # Only iterate up to the minimum length
                for j in range(song_count):
                    if i < len(songs_slices[j]):  # This check may not be necessary now but kept for safety
                        self.shredded_parts.append(songs_slices[j][i])
            progress_p1 = progress_p1 + 1
            self.signals.progressSignal.emit(int(progress_p1))

        else:
            for original_audio_location in self.original_audio_locations:
                song = AudioSegment.from_file(original_audio_location)
                sliced_list = list(song[::int(self.shred_length)])
                self.shredded_parts.extend(sliced_list)
                progress_p1 = progress_p1 + 1
                self.signals.progressSignal.emit(int(progress_p1))
            random.shuffle(self.shredded_parts)

        combined_song = AudioSegment.empty()
        progress_p2 = progress_p1
        for part in self.shredded_parts:
            combined_song += part
            progress_p2 = progress_p2 + 1
            percent = int((99-progress_p1) * progress_p2 / len(self.shredded_parts))
            self.signals.progressSignal.emit(progress_p1 + percent)

        self.signals.freeze_x.emit()
        QThread.msleep(100)

        filedir = os.path.dirname(self.original_audio_locations[0])  # Use the first file's directory
        combined_file_path = filedir + "/SHREDDED.mp3"
        combined_song.export(combined_file_path, format="mp3")

        self.signals.progressSignal.emit(int(100))
        self.signals.finish.emit(combined_file_path)


class Shredder(QWidget):
    def __init__(self, parent=None):
        super(Shredder, self).__init__(parent)

        layout = QFormLayout()
        hbox = QHBoxLayout()

        self.setAcceptDrops(True)

        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        # Join the base path with the filename to get the full path to the icon
        icon_path = os.path.join(base_path, 'icon.png')
        self.setWindowIcon(QtGui.QIcon(icon_path))

        self.setMinimumSize(500, 100)

        self.original_audio_locations = []
        self.shred_length = 1000
        self.operation_in_progress = False  # Flag to track if an operation is in progress

        self.btn_load = QPushButton("Select Song File(s) Or Drag && Drop")
        self.btn_load.clicked.connect(self.get_files)

        self.load_info = QLabel("File Location(s):")
        self.load_info.setAlignment(QtCore.Qt.AlignCenter)

        self.shred_length_user_input = QLineEdit(str(self.shred_length))
        self.shred_length_user_input.setValidator(QIntValidator(1, 9999))
        self.shred_length_user_input.setAlignment(Qt.AlignCenter)
        self.shred_length_user_input.textChanged.connect(self.update_shred_length)

        self.interlace_box = QCheckBox("Alternate Between Songs")

        self.btn_shred = QPushButton("Shred")
        self.btn_shred.clicked.connect(self.pass_shred)

        self.progressBar = QProgressBar(self)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

        hbox.addWidget(self.shred_length_user_input)
        hbox.addWidget(self.interlace_box)
        layout.addRow(self.btn_load)
        layout.addRow(self.load_info)
        layout.addRow("Shred Length (1-9999ms)", hbox)
        layout.addRow(self.btn_shred)
        layout.addRow(self.progressBar)

        self.setLayout(layout)
        self.setWindowTitle("SongShredder")
        self.threadpool = QThreadPool()

    def dragEnterEvent(self, event):
        # Check for the MIME data format we want
        mime = event.mimeData()
        if mime.hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # Get the list of dropped file URLs
        dropped_files = [url.toLocalFile() for url in event.mimeData().urls()]

        # Optional: Filter for audio files (you can improve this filter as needed)
        audio_files = [f for f in dropped_files if f.endswith(('.mp3', '.wav'))]

        if audio_files:
            self.original_audio_locations = audio_files
            self.load_info.setText("File Location(s): " + ", ".join(audio_files))

    def closeEvent(self, event):
        if self.operation_in_progress:
            event.ignore()
        else:
            event.accept()

    def update_operation(self):
        self.operation_in_progress = True

    def progress_update(self, value):
        self.progressBar.setValue(value)

    def open_file(self, file_path):
        self.load_info.setText("Created File Location: " + file_path)
        self.btn_shred.setEnabled(True)
        os.startfile(file_path)

    def finish_operation(self, file_path):
        self.operation_in_progress = False
        self.open_file(file_path)

    def update_shred_length(self, text):
        try:
            shred_length = int(text)
            if 1 <= shred_length <= 9999:
                self.shred_length = shred_length
        except ValueError:
            self.shred_length = 1000

    def get_files(self):
        self.original_audio_locations, _filter = QFileDialog.getOpenFileNames(self, 'Open Audio Files', '', "MP3/WAV ("
                                                                                                            "*.mp3 "
                                                                                                            "*.wav)")
        if self.original_audio_locations:
            string_list = [str(element) for element in self.original_audio_locations]
            delimiter = ", "
            result_string = delimiter.join(string_list)
            self.load_info.setText("File Location(s): " + result_string)

    def pass_shred(self):
        if not self.original_audio_locations:
            self.load_info.setText("You must select one or more audio files!")
        else:
            self.progressBar.setValue(0)
            # Checkbox is checked, do something
            self.btn_shred.setEnabled(False)
            interlace = self.interlace_box.isChecked()
            worker = Worker(self.shred_length, self.original_audio_locations, interlace, self)
            worker.signals.progressSignal.connect(self.progress_update)
            worker.signals.freeze_x.connect(self.update_operation)
            worker.signals.finish.connect(self.finish_operation)
            self.threadpool.start(worker)


def main():
    app = QApplication(sys.argv)
    ex = Shredder()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
