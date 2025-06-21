import time, os, json
import sqlite3, requests
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QAbstractItemView, QGridLayout, QLabel, QDialog,
    QComboBox, QLineEdit, QFileDialog, QTableWidget, QMessageBox, QScrollArea, QTableWidgetItem, QTextEdit
)
import sys
from PyQt6.QtCore import QMimeData, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDrag
from PyQt6.QtGui import QIcon

# File directory
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.getcwd())
connection = sqlite3.connect(os.path.join(BASE_DIR, 'jobs.db'), check_same_thread=False)

# Universal style for buttons and input fields (increased sizes)
button_style = "font-size: 18px; padding: 20px; min-width: 300px; font-family: 'Poppins', sans-serif;"
# Create Separation button style
cs_button_style = "font-size: 18px; padding: 20px; min-width: 300px; font-family: 'Poppins', sans-serif; background-color: #0176b3; border-radius: 0.3rem;"
input_style = "font-size: 18px; padding: 15px; min-width: 300px; font-family: 'Poppins', sans-serif;"  # Style for text fields and other elements
# Text style
label_style = "font-size: 16px; font-family: 'Poppins', sans-serif;"
small_label_style = "font-size: 12px; font-family: 'Poppins', sans-serif;"
combo_style = " font-size: 16px; font-family: 'Poppins'; padding: 20px; "

# Dialog background style
dialog_background = """
    background: linear-gradient(to bottom, blue, white);
    border: none;
    margin: 0;
    padding: 0;
"""

stylesheet = """
QWidget {
    # background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                stop: 0 #0176B3, stop: 0.5 #1E9BDC, stop: 1 #FFFFFF);
}
"""

path_hash_dict = {}
separation_n = 0


def create_separation(path_to_file, api_token, sep_type, add_opt1, add_opt2, add_opt3):
    files = {
        'audiofile': open(path_to_file, 'rb'),
        'api_token': (None, api_token),
        'sep_type': (None, sep_type),
        'add_opt1': (None, add_opt1),
        'add_opt2': (None, add_opt2),
        'add_opt3': (None, add_opt3),
        'output_format': (None, '1'),
        'is_demo': (None, '0'),
    }
    print("files")
    print(files)

    response = requests.post('https://mvsep.com/api/separation/create', files=files)
    if response.status_code == 200:
        response_content = response.content

        # Convert byte array to string
        string_response = response_content.decode('utf-8')

        # Parse string to JSON
        parsed_json = json.loads(string_response)

        # Output result
        hash = parsed_json["data"]["hash"]

        return hash, response.status_code
    else:
        return response.content, response.status_code


def get_separation_types():
    # URL for the request
    api_url = 'https://mvsep.com/api/app/algorithms'

    # Making a GET request
    response = requests.get(api_url)

    # Checking the response status code
    if response.status_code == 200:
        # Parsing the response to JSON
        data = response.json()
        result = {}  # Creating a new dictionary to store data by render_id
        algorithm_fields_result = {}

        # Data structure check (for debugging)
        if isinstance(data, list):  # Checking that data is a list
            for algorithm in data:
                if isinstance(algorithm, dict):  # Checking that each element is a dictionary
                    render_id = algorithm.get('render_id', 'N/A')
                    name = algorithm.get('name', 'N/A')
                    algorithm_group_id = algorithm.get('algorithm_group_id', 'N/A')
                    # print(f"{render_id}: {name}, Group ID: {algorithm_group_id}")

                    # Additional fields
                    algorithm_fields = algorithm.get('algorithm_fields', [])
                    for field in algorithm_fields:
                        if isinstance(field, dict):
                            field_name = field.get('name', 'N/A')
                            field_text = field.get('text', 'N/A')
                            field_options = field.get('options', 'N/A')
                            # Printing additional fields (can be removed if not needed)
                            # print(f"\tField Name: {field_name}, Field Text: {field_text}, Options: {field_options}")

                    # Algorithm descriptions
                    algorithm_descriptions = algorithm.get('algorithm_descriptions', [])
                    for description in algorithm_descriptions:
                        if isinstance(description, dict):
                            short_desc = description.get('short_description', 'N/A')
                            lang = description.get('lang', 'N/A')
                            # Printing algorithm description (can be removed if not needed)
                            # print(f"\tShort Description: {short_desc}, Language: {lang}")

                    # Saving data to result by render_id
                    result[render_id] = name
                    # Printing data for example
                    # print(f"{render_id}: {name}, Group ID: {algorithm_group_id}")

                    algorithm_fields_result[render_id] = algorithm_fields

        else:
            print(f"Unexpected top-level data format: {data}")

        # Returning the result (can be used for further processing)
        # print(result)
        return result, algorithm_fields_result
    else:
        print(f"Request failed with status code: {response.status_code}")


def download_file(url, filename, save_path):
    """
    Download the file from the specified URL and save it in the specified path.
    """
    print("start download")
    response = requests.get(url)
    print("end download")

    if response.status_code == 200:
        # Ensure the directory exists
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        file_path = os.path.join(save_path, filename)

        # Save the content of the response to the file
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return f"File '{filename}' uploaded successfully!"
    else:
        print(f"There was an error loading the file '{filename}'. Status code: {response.status_code}.")


def get_result(hash, save_path):
    success, data = check_result(hash)
    if success:
        try:
            files = data['data']['files']
        except KeyError:
            print("The separation is not ready yet.")
            return ""
        text = ""
        for file_info in files:
            url = file_info['url'].replace('\\/', '/')  # Correct slashes
            filename = file_info['download']  # File name for saving
            text += f'{download_file(url, filename, save_path)}\n'
        return text
    else:
        print("An error occurred while retrieving file data.")


def check_result(hash):
    params = {'hash': hash}
    response = requests.get('https://mvsep.com/api/separation/get', params=params)
    data = json.loads(response.content.decode('utf-8'))

    return data['success'], data


class SepThread(QThread):

    def __init__(self, api_token=None, data_table=None, base_dir_label=None):
        super(SepThread, self).__init__()
        self.data_table = data_table
        self.api_token = api_token
        self.base_dir_label = base_dir_label

    def run(self):
        # Creating a database connection (file my_database.db will be created)
        # self.connection = sqlite3.connect(os.path.join(BASE_DIR, 'jobs.db'), check_same_thread=False)
        global connection
        self.cursor = connection.cursor()

        while True:

            # checking running processes
            # self.cursor.execute('INSERT INTO Jobs (start_time, update_time, filename, out_dir, hash[5], status[6], separation, option1, option2, option3) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (int(time.time()), int(time.time()), path, self.output_dir, "", "Added", separation_type, option1, option2, option3))
            self.cursor.execute('SELECT * FROM Jobs ORDER BY id DESC')
            jobs = self.cursor.fetchall()
            for row, job in enumerate(jobs):
                # self.data_table.setHorizontalHeaderLabels(["ID", "Start Time", "FileName", "Out Dir", "Separation Type", "Adv.Opt #1", "Adv.Opt #2", "Adv.Opt #3", "Status", "Update Status"])
                # self.data_table.setHorizontalHeaderLabels(["ID", "FileName", "Separation Type""Status"])
                job_id = int(job[0])
                # self.data_table.setItem(row, 0, QTableWidgetItem(str(job_id)))
                # start_date = datetime.strptime(str(job[1]), '%Y-%m-%d %H:%M')
                start_date = datetime.fromtimestamp(job[1])
                start_date = str(start_date.strftime('%Y-%m-%d %H:%M'))

                file_name = os.path.basename(job[3])
                self.data_table.setItem(row, 0, QTableWidgetItem(file_name))

                out_dir = job[4]
                separation_type = str(job[7])
                self.data_table.setItem(row, 1, QTableWidgetItem(separation_type))  # separation
                """
                self.data_table.setItem(row, 5, QTableWidgetItem(job[8])) #  option1
                self.data_table.setItem(row, 6, QTableWidgetItem(job[9])) #  option2
                self.data_table.setItem(row, 7, QTableWidgetItem(job[10])) #  option 3
                """
                status = str(job[6])
                self.data_table.setItem(row, 2, QTableWidgetItem(status))  # status
                update_time = datetime.fromtimestamp(job[2])
                update_time = str(update_time.strftime('%H:%M:%S'))

                if job[6] == "Added":
                    # Attempting to start separation (e.g., generate hash or error)
                    # self.base_dir_label.setText(f"Token: {self.api_token}")

                    hash_val, status_code = create_separation(job[3], self.api_token, separation_type,
                                                              job[8], job[9], job[10])

                    if status_code == 200:  # Success with hash
                        self.cursor.execute('UPDATE Jobs SET hash = ? WHERE id = ?', (hash_val, job[0]))
                        self.cursor.execute('UPDATE Jobs SET status = ? WHERE id = ?', ("Process", job[0]))
                        self.cursor.execute('UPDATE Jobs SET update_time = ? WHERE id = ?', (int(time.time()), job[0]))

                        self.cursor.execute(
                            'INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                            (job_id, int(time.time()), "Added -> Process", ""))

                    else:
                        self.cursor.execute(
                            'INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                            (job_id, int(time.time()), "Error Start Process", f"response.content: {hash_val}"))
                        print("error start process")
                        print(hash_val)

                # connecting the thread to check separation progress
                if job[6] == "Process":
                    self.cursor.execute('UPDATE Jobs SET update_time = ? WHERE id = ?', (int(time.time()), job[0]))
                    self.cursor.execute('INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                                        (job_id, int(time.time()), "Process", f""))

                    params = {'hash': job[5]}
                    response = requests.get('https://mvsep.com/api/separation/get', params=params)
                    data = json.loads(response.content.decode('utf-8'))

                    if data['success']:
                        self.cursor.execute(
                            'INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                            (job_id, int(time.time()), "Process -> Success", f""))

                        files = []
                        try:
                            files = data['data']['files']
                        except KeyError:
                            pass
                            self.cursor.execute(
                                'INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                                (job_id, int(time.time()), "Process -> No Files", f""))

                        for file_info in files:
                            url = file_info['url'].replace('\\/', '/')  # Correct slashes
                            filename = file_info['download']  # File name for saving
                            # download_file(url, filename, save_path)
                            self.cursor.execute('UPDATE Jobs SET status = ? WHERE id = ?', ("Download", job[0]))
                            self.cursor.execute('UPDATE Jobs SET update_time = ? WHERE id = ?',
                                                (int(time.time()), job[0]))
                            self.cursor.execute(
                                'INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                                (job_id, int(time.time()), "Process -> Download", f"filename: {filename}"))

                            print(f"Start download: {url}")
                            response_dl = requests.get(url)  # Renamed to avoid conflict
                            if response_dl.status_code == 200:
                                # Ensure the directory exists
                                if not os.path.exists(job[4]):
                                    os.makedirs(job[4])
                                file_path = os.path.join(job[4], filename)
                                # Save the content of the response to the file
                                with open(file_path, 'wb') as f:
                                    f.write(response_dl.content)
                                    self.cursor.execute('UPDATE Jobs SET status = ? WHERE id = ?', ("Complete", job[0]))
                                self.cursor.execute(
                                    'INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                                    (job_id, int(time.time()), "Process -> Complete", f"filename: {filename}"))


                    else:
                        self.cursor.execute('UPDATE Jobs SET status = ? WHERE id = ?', ("Error", job[0]))
                        self.cursor.execute(
                            'INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                            (job_id, int(time.time()), "Process -> Error", f""))

            # self.data_table.resizeColumnsToContents()
            connection.commit()
            time.sleep(1)


class DragButton(QPushButton):
    dragged = pyqtSignal()

    def dragEnterEvent(self, e):
        print("dragEnterEvent")
        e.accept()

    def dropEvent(self, event):
        self.selected_files = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.selected_files.append(file_path)
            event.accept()
            self.dragged.emit()
        else:
            event.ignore()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Creating a database connection (file my_database.db will be created)
        global connection
        self.cursor = connection.cursor()

        # Creating table Jobs
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time INTEGER,
        update_time INTEGER,
        filename TEXT NOT NULL,
        out_dir TEXT NOT NULL,
        hash TEXT NOT NULL,
        status TEXT NOT NULL,
        separation INTEGER,
        option1 TEXT NOT NULL,
        option2 TEXT NOT NULL,
        option3 TEXT NOT NULL
        )
        ''')
        connection.commit()

        # Creating table Log
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        update_time INTEGER,
        action TEXT NOT NULL,
        comment TEXT NOT NULL
        )
        ''')
        connection.commit()

        self.setWindowTitle("MVSep.com API: Create Separation")
        self.setGeometry(50, 50, 400, 400)
        self.setFixedSize(740, 600)
        layout = QGridLayout()

        self.token_filename = os.path.join(BASE_DIR, "api_token.txt")
        self.selected_files = []
        if getattr(sys, 'frozen', False):
            self.output_dir = os.path.join(os.path.dirname(sys.executable), 'output/')
        else:
            self.output_dir = os.path.join(os.path.abspath(os.getcwd()), 'output/')
        if not os.path.exists(self.output_dir):  # Ensure output directory exists at startup
            os.makedirs(self.output_dir)
        self.algorithm_fields = {}

        self.alg_opt1 = {}
        self.alg_opt2 = {}
        self.alg_opt3 = {}

        self.selected_opt1 = "0"  # Defaulting to string "0" if these are option keys
        self.selected_opt2 = "0"
        self.selected_opt3 = "0"

        self.selected_algoritms_list = []

        self.data, self.algorithm_fields = get_separation_types()

        """
████████    █████    █████     ██        ███████
   ██      ██   ██   ██   ██   ██        ██
   ██      ███████   █████     ██        █████
   ██      ██   ██   ██   ██   ██   ██   ██
   ██      ██   ██   █████     ██████    ███████
        """
        # Create a table
        self.data_table = QTableWidget(self)
        self.data_table.setColumnCount(3)  # Set three columns
        self.data_table.setColumnWidth(0, 185)
        self.data_table.setColumnWidth(1, 100)
        self.data_table.setColumnWidth(2, 50)
        self.data_table.setRowCount(10)
        self.data_table.setHorizontalHeaderLabels(["FileName", "Separation Type", "Status"])
        self.data_table.setMinimumWidth(350)
        self.data_table.setMinimumHeight(350)
        # self.data_table.setAutoScroll(True)
        self.data_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        layout.addWidget(self.data_table, 0, 1, 7, 1,
                         alignment=Qt.AlignmentFlag.AlignTop)  # Span changed to match GUI better

        self.file_list_label = QLabel("Selected Files:")
        self.file_list_label.setStyleSheet(label_style)
        layout.addWidget(self.file_list_label, 7, 1, alignment=Qt.AlignmentFlag.AlignTop)
        # text field for the list of files
        self.file_list_text = QTextEdit(self)
        self.file_list_text.toPlainText()
        layout.addWidget(self.file_list_text, 8, 1, 3, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Field for API Token
        self.api_label = QLabel("API Token")
        self.api_label.setStyleSheet(label_style)
        self.api_input = QLineEdit()
        self.api_input.setStyleSheet(input_style)
        # looking for a file with a token
        if os.path.isfile(self.token_filename):
            with open(self.token_filename, "r") as f:
                api_token = f.read().strip()
                if len(api_token) == 30:
                    self.api_input.setText(api_token)

        layout.addWidget(self.api_label, 0, 0)
        layout.addWidget(self.api_input, 1, 0)

        # Link for API Token
        self.api_link_label = QLabel("<a href='https://mvsep.com/ru/full_api'>Get Token</a>")
        self.api_link_label.setStyleSheet(label_style)
        self.api_link_label.setOpenExternalLinks(True)
        layout.addWidget(self.api_link_label, 2, 0)

        # Button to launch the master
        self.master_button = QPushButton("Algorithms Master")
        self.master_button.setAcceptDrops(True)
        self.master_button.setStyleSheet(button_style)
        self.master_button.clicked.connect(self.start_master)
        layout.addWidget(self.master_button, 3, 0)

        # Selected audio file
        self.filename_label = QLabel("Audio selected:")
        self.filename_label.setStyleSheet(label_style)
        self.filename_label.setOpenExternalLinks(True)  # This might not be intended for filename_label
        layout.addWidget(self.filename_label, 4, 0)
        # Button to select file
        self.file_button = DragButton("Select File")
        self.file_button.setAcceptDrops(True)
        self.file_button.setStyleSheet(button_style)
        self.file_button.clicked.connect(self.select_file)
        self.file_button.dragged.connect(self.select_drag_file)

        layout.addWidget(self.file_button, 5, 0)

        # Clear selected files
        self.clear_files_button = QPushButton("Clear Files")
        self.clear_files_button.setStyleSheet(button_style)
        self.clear_files_button.clicked.connect(self.clear_files)
        layout.addWidget(self.clear_files_button, 6, 0)

        # Selected directory
        self.output_dir_label = QLabel(f"Output Dir: {self.output_dir}")
        self.output_dir_label.setStyleSheet(label_style)
        layout.addWidget(self.output_dir_label, 7, 0)
        # Button to select results directory
        self.output_dir_button = QPushButton("Select Output Dir")
        self.output_dir_button.setStyleSheet(button_style)
        self.output_dir_button.clicked.connect(self.select_output_dir)
        layout.addWidget(self.output_dir_button, 8, 0)

        # Button to create separation
        self.create_button = QPushButton("Create Separation")
        self.create_button.setStyleSheet(cs_button_style)
        self.create_button.clicked.connect(self.process_separation)
        layout.addWidget(self.create_button, 9, 0)

        # Base Dir
        self.base_dir_label = QLabel(f"Base Dir: {BASE_DIR}")
        self.base_dir_label.setStyleSheet(small_label_style)
        layout.addWidget(self.base_dir_label, 10, 0)

        self.setLayout(layout)
        # self.connection.close()

        # connecting the thread to check separation progress

        self.st = SepThread(api_token=self.api_input.text(), data_table=self.data_table,
                            base_dir_label=self.base_dir_label)
        self.st.start()

    def clear_files(self):
        self.selected_files = []
        self.filename_label.setText(f"No Audio selected:")
        # adding to TextEdit
        self.file_list_text.setText("")

    def select_file(self):
        # Opening dialog to select file(s)
        selected_files_tuple = QFileDialog.getOpenFileNames(self, "Select File", "", "Audio Files (*.mp3 *.wav *.flac *m4a *mp4)")
        if selected_files_tuple and selected_files_tuple[0]:  # Check if files were selected
            self.selected_files = selected_files_tuple[0]
            print(f"Files selected:")
            print(self.selected_files)
            if len(self.selected_files) > 0:
                self.filename_label.setText(f"Audio selected: {os.path.basename(self.selected_files[0])}...")
                # adding to TextEdit
                self.file_list_text.setText("")
                selected_files_text = "\n".join(self.selected_files)
                self.file_list_text.setText(selected_files_text)
                self.create_button.setText("Create Separation")
        else:
            self.selected_files = []  # Ensure it's empty if dialog is cancelled
            self.filename_label.setText("No Audio selected:")
            self.file_list_text.setText("")

    def select_drag_file(self):
        self.selected_files = self.file_button.selected_files
        print(f"Files selected:")
        print(self.selected_files)
        if len(self.selected_files) > 0:
            self.filename_label.setText(f"Audio selected: {os.path.basename(self.selected_files[0])}...")
            # adding to TextEdit
            self.file_list_text.setText("")
            selected_files_text = "\n".join(self.selected_files)
            self.file_list_text.setText(selected_files_text)

            self.create_button.setText("Create Separation")

    def on_selection_change(self, index):  # This method appears unused in the current main window context
        # Getting the selected text
        selected_item = self.type_combo.currentText()  # type_combo is not defined in MainWindow scope

        # Searching for the corresponding key for the selected value
        for key, value in self.data.items():
            if value == selected_item:
                self.selected_key = key
                print(f"Selected key: {self.selected_key} - {selected_item}")

                selected_algorithm = self.algorithm_fields[key]
                print("Options Len:")
                print(len(selected_algorithm))
                print("Options:")
                print(selected_algorithm)

                # clearing all ComboBoxes
                self.option1_combo.clear()  # option1_combo is not defined in MainWindow scope
                self.option2_combo.clear()  # option2_combo is not defined in MainWindow scope
                self.option3_combo.clear()  # option3_combo is not defined in MainWindow scope
                self.option1_label.setText("Additional Option 1")  # option1_label is not defined in MainWindow scope
                self.option2_label.setText("Additional Option 2")  # option2_label is not defined in MainWindow scope
                self.option3_label.setText("Additional Option 3")  # option3_label is not defined in MainWindow scope

                if len(self.algorithm_fields[key]) > 0:
                    self.option1_label.setText(f"Additional Option 1: {selected_algorithm[0]['text']}")
                    self.alg_opt1 = json.loads(selected_algorithm[0]['options'])
                    # Sorting the dictionary by key
                    sorted_data = {k: v for k, v in sorted(self.alg_opt1.items())}
                    value_items = sorted_data.values()  # Renamed to avoid conflict
                    # Adding items to the combobox
                    self.option1_combo.addItems(value_items)

                if len(self.algorithm_fields[key]) > 1:
                    self.option2_label.setText(f"Additional Option 2: {selected_algorithm[1]['text']}")
                    self.alg_opt2 = json.loads(selected_algorithm[1]['options'])
                    # Sorting the dictionary by key
                    sorted_data = {k: v for k, v in sorted(self.alg_opt2.items())}
                    value_items = sorted_data.values()  # Renamed to avoid conflict
                    # Adding items to the combobox
                    self.option2_combo.addItems(value_items)

                if len(self.algorithm_fields[key]) > 2:
                    self.option3_label.setText(f"Additional Option 3: {selected_algorithm[2]['text']}")
                    self.alg_opt3 = json.loads(selected_algorithm[2]['options'])
                    # Sorting the dictionary by key
                    sorted_data = {k: v for k, v in sorted(self.alg_opt3.items())}
                    value_items = sorted_data.values()  # Renamed to avoid conflict
                    # Adding items to the combobox
                    self.option3_combo.addItems(value_items)

                break

    def on_change_option1(self, index):  # This method appears unused
        # Getting the selected text
        selected_item = self.option1_combo.currentText()  # option1_combo is not defined in MainWindow scope
        # Searching for the corresponding key for the selected value
        for key, value in self.alg_opt1.items():
            if value == selected_item:
                self.selected_opt1 = key
                break

    def on_change_option2(self, index):  # This method appears unused
        # Getting the selected text
        selected_item = self.option2_combo.currentText()  # option2_combo is not defined in MainWindow scope
        # Searching for the corresponding key for the selected value
        for key, value in self.alg_opt2.items():
            if value == selected_item:
                self.selected_opt2 = key
                break

    def on_change_option3(self, index):  # This method appears unused
        # Getting the selected text
        selected_item = self.option3_combo.currentText()  # option3_combo is not defined in MainWindow scope
        # Searching for the corresponding key for the selected value
        for key, value in self.alg_opt3.items():
            if value == selected_item:
                self.selected_opt3 = key
                break

    def select_output_dir(self):
        # Opening dialog to select folder
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Folder to Save")
        if selected_dir:  # Check if a directory was selected
            self.output_dir = selected_dir
            self.output_dir_label.setText(f"Output Dir: {self.output_dir}")

    def process_separation(self):
        global path_hash_dict, separation_n, connection

        api_token = self.api_input.text()

        # Clear field styles before validation
        self.clear_styles()
        # Validation
        valid = True
        if len(self.selected_files) == 0:  # If file is not selected
            self.file_button.setStyleSheet(
                "background-color: red; font-size: 18px; padding: 20px; min-width: 300px;")  # Highlighting the button in red
            valid = False
        if not api_token:  # If API token is empty
            self.api_input.setStyleSheet("border: 2px solid red; font-size: 18px; padding: 15px; min-width: 300px;")
            valid = False
        else:
            # save to file
            with open(self.token_filename, "w") as f:
                f.write(api_token)

        if len(self.selected_algoritms_list) == 0:  # If separation type is not selected (via master)
            # This validation logic might need adjustment if a single default algorithm is intended
            # For now, it implies master must be used to select at least one algorithm.
            self.master_button.setStyleSheet(
                f"border: 2px solid red; {button_style}")  # Use button_style for consistency
            valid = False

        # Check: if there are errors, do not continue the process
        if not valid:
            if os.name == 'nt':  # For Windows
                os.system('cls')
            else:  # For Linux/MacOS
                os.system('clear')
            print("Error separation:")
            print(f"API Token provided: {'Yes' if api_token else 'No'}")
            print(f"Files selected: {len(self.selected_files)}")
            print(f"Algorithms selected: {len(self.selected_algoritms_list)}")
            return

        self.st.api_token = self.api_input.text()
        """
        start_time INTEGER,
        update_time INTEGER,
        filename TEXT NOT NULL,
        out_dir TEXT NOT NULL,
        hash TEXT NOT NULL,
        status TEXT NOT NULL,
        separation INTEGER,
        option1 TEXT NOT NULL,
        option2 TEXT NOT NULL,
        option3 TEXT NOT NULL,

        """
        # This 'else' block for when selected_algoritms_list is empty was problematic
        # as separation_type, option1 etc. were not defined.
        # The logic now strictly relies on selected_algoritms_list.
        # If a default/single separation without master was intended, it needs to be explicitly handled.

        if len(self.selected_algoritms_list) > 0:
            for new_item in self.selected_algoritms_list:
                separation_type = new_item["selected_key"]
                option1 = new_item["selected_opt1"]
                option2 = new_item["selected_opt2"]
                option3 = new_item["selected_opt3"]

                for file_path in self.selected_files:  # Renamed 'file' to 'file_path'
                    # Adding a new job
                    self.cursor.execute(
                        'INSERT INTO Jobs (start_time, update_time, filename, out_dir, hash, status, separation, option1, option2, option3) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (int(time.time()), int(time.time()), file_path, self.output_dir, "", "Added", separation_type,
                         str(option1), str(option2), str(option3)))  # Ensure options are strings
                    connection.commit()

                    self.cursor.execute('SELECT * FROM Jobs ORDER BY id DESC LIMIT 0,1')
                    jobs = self.cursor.fetchall()
                    job_id = -1  # Default value
                    if jobs:
                        job_id = int(jobs[0][0])
                    print(f"job_id: {job_id}")

                    # Logging
                    """
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    update_time INTEGER,
                    action TEXT NOT NULL,
                    comment TEXT NOT NULL

                    """
                    if job_id != -1:
                        self.cursor.execute(
                            'INSERT INTO Log (job_id, update_time, action, comment) VALUES (?, ?, ?, ?)',
                            (job_id, int(time.time()), "Added from Master", ""))
                        connection.commit()

            # self.selected_algoritms_list = [] # Clearing list after processing might be desired depending on workflow

        self.create_button.setText("Create Separation +")

    def stop_separation(self, result_text):
        global separation_n
        # completing separation
        QMessageBox.information(self, "Result", result_text)
        self.create_button.setText(f"Create Separation: [{separation_n}]")

    def clear_styles(self):
        # Reset styles
        self.master_button.setStyleSheet(button_style)
        self.file_button.setStyleSheet(button_style)
        self.api_input.setStyleSheet(input_style)

    def start_separation(self, separation_type, api_token, option1, option2, option3,
                         path):  # This method appears unused
        hash_val, status_code = create_separation(path, api_token, separation_type, option1, option2,
                                                  option3)
        if status_code == 200:
            return {"success": True, "hash": hash_val}  # Success with hash
        else:
            return {"success": False, "error": hash_val}

    """
███    ███    █████     ██████   ████████   ███████   ███████
██ █  █ ██   ██   ██   ██           ██      ██        ██    ██
██  ██  ██   ███████    █████       ██      █████     ███████
██      ██   ██   ██        ██      ██      ██        ██  ██
██      ██   ██   ██   ██████       ██      ███████   ██    ██
    """

    def start_master(self):
        # Creating a form to display separation types
        separation_dialog = QDialog(self)
        separation_dialog.setWindowTitle("Separation Types")
        # separation_dialog.setGeometry(50, 50, 400, 400)
        separation_dialog.setFixedSize(740, 600)

        layout = QGridLayout(separation_dialog)

        # Separation type selection field
        self.type_label_master = QLabel("Separation Type")
        self.type_label_master.setStyleSheet(label_style)

        self.data, self.algorithm_fields = get_separation_types()

        # Sorting the dictionary by key
        sorted_data = {k: v for k, v in sorted(self.data.items())}

        # Initializing QComboBox
        self.type_combo_master = QComboBox(separation_dialog)  # Parent should be dialog
        value_items = sorted_data.values()  # Renamed
        # Adding items to the combobox
        self.type_combo_master.addItems(list(value_items))  # Ensure it's a list of strings

        # Setting up handler for selection
        self.type_combo_master.currentIndexChanged.connect(self.on_selection_master_change)

        self.type_combo_master.setStyleSheet(combo_style)
        layout.addWidget(self.type_label_master, 0, 0)
        layout.addWidget(self.type_combo_master, 1, 0)

        # Adding additional options 1, 2, 3
        self.option1_label_master = QLabel("Additional Option 1")
        self.option1_label_master.setStyleSheet(label_style)
        # Initializing QComboBox
        self.option1_combo_master = QComboBox(separation_dialog)  # Parent should be dialog
        self.option1_combo_master.setStyleSheet(combo_style)
        # Setting up handler for selection
        self.option1_combo_master.currentIndexChanged.connect(self.on_change_master_option1)
        layout.addWidget(self.option1_label_master, 2, 0)
        layout.addWidget(self.option1_combo_master, 3, 0)

        # Adding additional options 1, 2, 3
        self.option2_label_master = QLabel("Additional Option 2")
        self.option2_label_master.setStyleSheet(label_style)
        # Initializing QComboBox
        self.option2_combo_master = QComboBox(separation_dialog)  # Parent should be dialog
        self.option2_combo_master.setStyleSheet(combo_style)
        # Setting up handler for selection
        self.option2_combo_master.currentIndexChanged.connect(self.on_change_master_option2)
        layout.addWidget(self.option2_label_master, 4, 0)
        layout.addWidget(self.option2_combo_master, 5, 0)

        # Adding additional options 1, 2, 3
        self.option3_label_master = QLabel("Additional Option 3")
        self.option3_label_master.setStyleSheet(label_style)
        # Initializing QComboBox
        self.option3_combo_master = QComboBox(separation_dialog)  # Parent should be dialog
        self.option3_combo_master.setStyleSheet(combo_style)
        # Setting up handler for selection
        self.option3_combo_master.currentIndexChanged.connect(self.on_change_master_option3)
        layout.addWidget(self.option3_label_master, 6, 0)
        layout.addWidget(self.option3_combo_master, 7, 0)

        # Trigger initial population of options
        if self.type_combo_master.count() > 0:
            self.on_selection_master_change(0)

        # Creating a button to add an algorithm
        add_button = QPushButton("Add Algorithm", separation_dialog)
        add_button.setStyleSheet(button_style)  # Applying style to buttons
        add_button.clicked.connect(self.add_algoritm)
        layout.addWidget(add_button, 8, 0)

        # RIGHT COLUMN
        self.algo_list_label = QLabel("Selected Algorithms:")
        self.algo_list_label.setStyleSheet(label_style)
        layout.addWidget(self.algo_list_label, 0, 1, alignment=Qt.AlignmentFlag.AlignTop)
        # text field for the list of algorithms
        self.algo_list_text = QTextEdit(separation_dialog)  # Parent should be dialog
        self.algo_list_text.setPlainText("")  # Use setPlainText
        self.algo_list_text.setMinimumWidth(350)
        self.algo_list_text.setMinimumHeight(386)
        layout.addWidget(self.algo_list_text, 1, 1, 7, 1, alignment=Qt.AlignmentFlag.AlignTop)  # Adjusted span

        # filling the text field
        self._update_algo_list_text()  # Helper function to update text

        # Creating a button to close the form
        close_button = QPushButton("Select Algorithms", separation_dialog)
        close_button.setStyleSheet(button_style)  # Applying style to buttons
        close_button.clicked.connect(separation_dialog.accept)
        layout.addWidget(close_button, 8, 1)  # Positioned below list

        # Creating a button to clear algorithms
        clear_algo_button = QPushButton("Clear Algorithms", separation_dialog)
        clear_algo_button.setStyleSheet(button_style)  # Applying style to buttons
        clear_algo_button.clicked.connect(self.clear_algo)
        layout.addWidget(clear_algo_button, 9, 0, 1, 2)  # Span across both columns

        # Setting layout in the dialog window
        separation_dialog.setLayout(layout)

        # Displaying the dialog window
        separation_dialog.exec()

    def _update_algo_list_text(self):
        selected_algo_text = ""
        for new_item in self.selected_algoritms_list:
            key = new_item["selected_key"]
            selected_opt1 = str(new_item["selected_opt1"])  # Ensure string for dict key
            selected_opt2 = str(new_item["selected_opt2"])
            selected_opt3 = str(new_item["selected_opt3"])

            alg_name = self.data.get(key, "Unknown Algorithm")
            selected_algo_text += f"{alg_name}"

            current_algorithm_fields = self.algorithm_fields.get(key, [])

            if len(current_algorithm_fields) > 0:
                alg_opt1_data = json.loads(current_algorithm_fields[0].get('options', '{}'))
                opt1_text = alg_opt1_data.get(selected_opt1, f"Opt1Val-{selected_opt1}")
                selected_algo_text += f": {opt1_text}"
            if len(current_algorithm_fields) > 1:
                alg_opt2_data = json.loads(current_algorithm_fields[1].get('options', '{}'))
                opt2_text = alg_opt2_data.get(selected_opt2, f"Opt2Val-{selected_opt2}")
                selected_algo_text += f", {opt2_text}"
            if len(current_algorithm_fields) > 2:
                alg_opt3_data = json.loads(current_algorithm_fields[2].get('options', '{}'))
                opt3_text = alg_opt3_data.get(selected_opt3, f"Opt3Val-{selected_opt3}")
                selected_algo_text += f", {opt3_text}"

            selected_algo_text += f"\n"
        self.algo_list_text.setPlainText(selected_algo_text)

    def clear_algo(self):
        self.selected_algoritms_list = []
        self._update_algo_list_text()

    def add_algoritm(self):
        # Getting the selected text
        selected_item_text = self.type_combo_master.currentText()
        separation_type_key = None  # Initialize
        for key, value in self.data.items():
            if value == selected_item_text:
                separation_type_key = key
                break

        # It's good practice to reset styles from previous errors
        self.type_combo_master.setStyleSheet(combo_style)  # Reset style

        if not separation_type_key:  # If separation type is not selected or not found
            self.type_combo_master.setStyleSheet(f"border: 2px solid red; {combo_style}")
            QMessageBox.warning(self, "Error", "Please select a valid separation type.")
            return

        new_item = {}
        new_item["selected_key"] = separation_type_key
        new_item["selected_opt1"] = self.selected_opt1  # These are set by on_change_master_optionX
        new_item["selected_opt2"] = self.selected_opt2
        new_item["selected_opt3"] = self.selected_opt3
        self.selected_algoritms_list.append(new_item)

        # filling the text field
        self._update_algo_list_text()

    def on_selection_master_change(self, index):
        # Getting the selected text
        selected_item_text = self.type_combo_master.currentText()
        self.selected_key = None  # Reset

        # Searching for the corresponding key for the selected value
        for key, value in self.data.items():
            if value == selected_item_text:
                self.selected_key = key
                break

        if not self.selected_key: return  # Should not happen if combo is populated correctly

        current_algorithm_fields = self.algorithm_fields.get(self.selected_key, [])

        # clearing all ComboBoxes in the master window
        self.option1_combo_master.clear()
        self.option2_combo_master.clear()
        self.option3_combo_master.clear()
        self.option1_label_master.setText("Additional Option 1")
        self.option2_label_master.setText("Additional Option 2")
        self.option3_label_master.setText("Additional Option 3")

        # Reset selected options to defaults (e.g., first item or "0")
        self.selected_opt1 = "0"
        self.selected_opt2 = "0"
        self.selected_opt3 = "0"

        if len(current_algorithm_fields) > 0:
            field1_info = current_algorithm_fields[0]
            self.option1_label_master.setText(f"Option 1: {field1_info.get('text', 'N/A')}")
            self.alg_opt1 = json.loads(field1_info.get('options', '{}'))
            # Sorting the dictionary by key (assuming keys are sortable, e.g., numbers as strings)
            try:  # Handle cases where keys might not be directly sortable as integers
                sorted_data_opt1 = {k: v for k, v in sorted(self.alg_opt1.items(), key=lambda item: int(item[0]))}
            except ValueError:
                sorted_data_opt1 = {k: v for k, v in sorted(self.alg_opt1.items())}

            value_items1 = list(sorted_data_opt1.values())
            # Adding items to the combobox
            self.option1_combo_master.addItems(value_items1)
            if value_items1: self.on_change_master_option1(0)  # Set default

        if len(current_algorithm_fields) > 1:
            field2_info = current_algorithm_fields[1]
            self.option2_label_master.setText(f"Option 2: {field2_info.get('text', 'N/A')}")
            self.alg_opt2 = json.loads(field2_info.get('options', '{}'))
            try:
                sorted_data_opt2 = {k: v for k, v in sorted(self.alg_opt2.items(), key=lambda item: int(item[0]))}
            except ValueError:
                sorted_data_opt2 = {k: v for k, v in sorted(self.alg_opt2.items())}
            value_items2 = list(sorted_data_opt2.values())
            self.option2_combo_master.addItems(value_items2)
            if value_items2: self.on_change_master_option2(0)

        if len(current_algorithm_fields) > 2:
            field3_info = current_algorithm_fields[2]
            self.option3_label_master.setText(f"Option 3: {field3_info.get('text', 'N/A')}")
            self.alg_opt3 = json.loads(field3_info.get('options', '{}'))
            try:
                sorted_data_opt3 = {k: v for k, v in sorted(self.alg_opt3.items(), key=lambda item: int(item[0]))}
            except ValueError:
                sorted_data_opt3 = {k: v for k, v in sorted(self.alg_opt3.items())}
            value_items3 = list(sorted_data_opt3.values())
            self.option3_combo_master.addItems(value_items3)
            if value_items3: self.on_change_master_option3(0)

    def on_change_master_option1(self, index):
        # Getting the selected text
        selected_item_text = self.option1_combo_master.currentText()
        # Searching for the corresponding key for the selected value
        for key, value in self.alg_opt1.items():
            if value == selected_item_text:
                self.selected_opt1 = key
                break

    def on_change_master_option2(self, index):
        # Getting the selected text
        selected_item_text = self.option2_combo_master.currentText()
        # Searching for the corresponding key for the selected value
        for key, value in self.alg_opt2.items():
            if value == selected_item_text:
                self.selected_opt2 = key
                break

    def on_change_master_option3(self, index):
        # Getting the selected text
        selected_item_text = self.option3_combo_master.currentText()
        # Searching for the corresponding key for the selected value
        for key, value in self.alg_opt3.items():
            if value == selected_item_text:
                self.selected_opt3 = key
                break


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    icon_path = os.path.join(BASE_DIR, 'mvsep.ico')
    main_window.setWindowIcon(QIcon(icon_path))
    app.setWindowIcon(QIcon(icon_path))
    main_window.show()
    sys.exit(app.exec())