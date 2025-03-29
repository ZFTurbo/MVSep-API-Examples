import time, os, json

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QDialog,
    QComboBox, QLineEdit, QFileDialog, QSpinBox, QMessageBox, QScrollArea
)
import sys
import requests
import json
from PyQt6.QtCore import QMimeData, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDrag

# File directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Universal style for buttons and input fields (increased sizes)
button_style = "font-size: 18px; padding: 20px; min-width: 300px; font-family: 'Poppins', sans-serif;"
# Create Separation style
cs_button_style = "font-size: 18px; padding: 20px; min-width: 300px; font-family: 'Poppins', sans-serif; background-color: #0176b3; border-radius: 0.3rem;"
input_style = "font-size: 18px; padding: 15px; min-width: 300px; font-family: 'Poppins', sans-serif;"  # Style for text fields and other elements
# Setting the text style
label_style = "font-size: 16px; font-family: 'Poppins', sans-serif;"
combo_style = " font-size: 16px; font-family: 'Poppins'; padding: 20px; "

# Style for dialog backgrounds
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


def get_separation_types():
    # Request URL
    api_url = 'https://mvsep.com/api/app/algorithms'

    # Making a GET request
    response = requests.get(api_url)

    # Checking the response status code
    if response.status_code == 200:
        # Parsing the response into JSON
        data = response.json()
        result = {}  # Creating a new dictionary to save data by render_id
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
        return f"File '{filename}' was downloaded successfully!"
    else:
        print(f"There was an error downloading the file '{filename}'. Status code: {response.status_code}.")


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


def create_separation(path_to_file, api_token, sep_type, add_opt1, add_opt2, add_opt3):
    files = {
        'audiofile': open(path_to_file, 'rb'),
        'api_token': (None, api_token),
        'sep_type': (None, sep_type),
        'add_opt1': (None, add_opt1),
        'add_opt2': (None, add_opt2),
        'add_opt3': (None, add_opt3),
        'output_format': (None, '1'),
        'is_demo': (None, '1'),
    }
    print("files")
    print(files)

    response = requests.post('https://mvsep.com/api/separation/create', files=files)
    if response.status_code == 200:
        response_content = response.content

        # Converting byte array to string
        string_response = response_content.decode('utf-8')

        # Parsing string into JSON
        parsed_json = json.loads(string_response)

        # Outputting the result
        hash = parsed_json["data"]["hash"]

        return hash, response.status_code
    else:
        return response.content, response.status_code


class SepThread(QThread):
    stop_separation_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super(SepThread, self).__init__(parent)
        self.hash = ""

    def run(self):
        global separation_n, path_hash_dict
        i = 0
        while i < 180:
            # Getting the result
            output_dir = path_hash_dict[self.hash]
            result_text = get_result(self.hash, output_dir)
            print(f"i={i}; {self.hash}")
            print(path_hash_dict)
            if result_text != "":
                # Displaying the text result in the dialog
                separation_n -= 1
                print("good separation break")
                print(result_text)
                self.stop_separation_signal.emit(result_text)
                break
            else:
                i += 1
                time.sleep(1)
            print()

        if i == 179:
            # Displaying a negative result in the dialog
            separation_n -= 1
            self.stop_separation_signal.emit("No result per 3 min.")


class DragButton(QPushButton):
    dragged = pyqtSignal()

    def dragEnterEvent(self, e):
        print("dragEnterEvent")
        e.accept()

    def dropEvent(self, event):
        self.selected_file = ""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.selected_file = file_path
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

        self.setWindowTitle("MVSep Separator GUI")
        self.setGeometry(50, 50, 400, 400)
        self.setFixedSize(400, 800)
        layout = QVBoxLayout()

        self.token_filename = os.path.join(BASE_DIR, "api_token.txt")
        self.selected_file = None
        self.output_dir = BASE_DIR + '/'
        self.algorithm_fields = {}

        self.alg_opt1 = {}
        self.alg_opt2 = {}
        self.alg_opt3 = {}

        self.selected_opt1 = 0
        self.selected_opt2 = 0
        self.selected_opt3 = 0

        # Separation type selection field
        self.type_label = QLabel("Separation Type")
        self.type_label.setStyleSheet(label_style)

        self.data, self.algorithm_fields = get_separation_types()

        # Sorting the dictionary by key
        sorted_data = {k: v for k, v in sorted(self.data.items())}

        # Initializing QComboBox
        self.type_combo = QComboBox(self)
        value = sorted_data.values()
        # Adding items to the combobox
        self.type_combo.addItems(value)

        # Setting up the selection handler
        self.type_combo.currentIndexChanged.connect(self.on_selection_change)

        self.type_combo.setStyleSheet(combo_style)
        layout.addWidget(self.type_label)
        layout.addWidget(self.type_combo)

        # API Token field
        self.api_label = QLabel("API Token")
        self.api_label.setStyleSheet(label_style)
        self.api_input = QLineEdit()
        self.api_input.setStyleSheet(input_style)
        # Looking for the token file
        if os.path.isfile(self.token_filename):
            with open(self.token_filename, "r") as f:
                api_token = f.read().strip()
                if len(api_token) == 30:
                    self.api_input.setText(api_token)

        layout.addWidget(self.api_label)
        layout.addWidget(self.api_input)

        # API Token link
        self.api_link_label = QLabel("<a href='https://mvsep.com/ru/full_api'>Get Token</a>")
        self.api_link_label.setStyleSheet(label_style)
        self.api_link_label.setOpenExternalLinks(True)
        layout.addWidget(self.api_link_label)

        # Adding additional options 1, 2, 3
        self.option1_label = QLabel("Additional Option 1")
        self.option1_label.setStyleSheet(label_style)

        # Initializing QComboBox
        self.option1_combo = QComboBox(self)
        self.option1_combo.setStyleSheet(combo_style)

        # Setting up the selection handler
        self.option1_combo.currentIndexChanged.connect(self.on_change_option1)
        layout.addWidget(self.option1_label)
        layout.addWidget(self.option1_combo)

        # Adding additional options 1, 2, 3
        self.option2_label = QLabel("Additional Option 2")
        self.option2_label.setStyleSheet(label_style)

        # Initializing QComboBox
        self.option2_combo = QComboBox(self)
        self.option2_combo.setStyleSheet(combo_style)

        # Setting up the selection handler
        self.option2_combo.currentIndexChanged.connect(self.on_change_option2)
        layout.addWidget(self.option2_label)
        layout.addWidget(self.option2_combo)

        # Adding additional options 1, 2, 3
        self.option3_label = QLabel("Additional Option 3")
        self.option3_label.setStyleSheet(label_style)

        # Initializing QComboBox
        self.option3_combo = QComboBox(self)
        self.option3_combo.setStyleSheet(combo_style)

        # Setting up the selection handler
        self.option3_combo.currentIndexChanged.connect(self.on_change_option3)
        layout.addWidget(self.option3_label)
        layout.addWidget(self.option3_combo)

        # Selected audio file
        self.filename_label = QLabel("Audio selected:")
        self.filename_label.setStyleSheet(label_style)
        self.filename_label.setOpenExternalLinks(True)
        layout.addWidget(self.filename_label)

        # File selection button
        self.file_button = DragButton("Select File")
        self.file_button.setAcceptDrops(True)
        self.file_button.setStyleSheet(button_style)
        self.file_button.clicked.connect(self.select_file)
        self.file_button.dragged.connect(self.select_drag_file)

        layout.addWidget(self.file_button)

        # Selected output directory
        self.output_dir_label = QLabel(f"Output Dir: {self.output_dir}")
        self.output_dir_label.setStyleSheet(label_style)
        layout.addWidget(self.output_dir_label)
        # Button for selecting the output directory
        self.output_dir_button = QPushButton("Select Output Dir")
        self.output_dir_button.setStyleSheet(button_style)
        self.output_dir_button.clicked.connect(self.select_output_dir)
        layout.addWidget(self.output_dir_button)

        # Button to create separation
        self.create_button = QPushButton("Create Separation")
        self.create_button.setStyleSheet(cs_button_style)
        self.create_button.clicked.connect(self.process_separation)
        layout.addWidget(self.create_button)

        self.setLayout(layout)

    def select_file(self):
        # Opening a dialog to select a file
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Audio Files (*.mp3 *.wav)")
        if file_path:
            self.selected_file = file_path
            print(f"File selected: {self.selected_file}")
            self.filename_label.setText(f"Audio selected: {os.path.basename(self.selected_file)}")

    def select_drag_file(self):
        self.selected_file = self.file_button.selected_file
        print(f"File selected: {self.selected_file}")
        self.filename_label.setText(f"Audio selected: {os.path.basename(self.selected_file)}")

    def on_selection_change(self, index):
        # Getting the selected text
        selected_item = self.type_combo.currentText()

        # Finding the corresponding key for the selected value
        for key, value in self.data.items():
            if value == selected_item:
                self.selected_key = key
                print(f"Selected key: {self.selected_key} - {selected_item}")

                selected_algorithm = self.algorithm_fields[key]
                print("Options Len:")
                print(len(selected_algorithm))
                print("Options:")
                print(selected_algorithm)

                # Clearing all ComboBoxes
                self.option1_combo.clear()
                self.option2_combo.clear()
                self.option3_combo.clear()
                self.option1_label.setText("Additional Option 1")
                self.option2_label.setText("Additional Option 2")
                self.option3_label.setText("Additional Option 3")

                if len(self.algorithm_fields[key]) > 0:
                    self.option1_label.setText(f"Additional Option 1: {selected_algorithm[0]['text']}")
                    self.alg_opt1 = json.loads(selected_algorithm[0]['options'])
                    # Sorting the dictionary by key
                    sorted_data = {k: v for k, v in sorted(self.alg_opt1.items())}
                    value = sorted_data.values()
                    # Adding items to the combobox
                    self.option1_combo.addItems(value)

                if len(self.algorithm_fields[key]) > 1:
                    self.option2_label.setText(f"Additional Option 2: {selected_algorithm[1]['text']}")
                    self.alg_opt2 = json.loads(selected_algorithm[1]['options'])
                    # Sorting the dictionary by key
                    sorted_data = {k: v for k, v in sorted(self.alg_opt2.items())}
                    value = sorted_data.values()
                    # Adding items to the combobox
                    self.option2_combo.addItems(value)

                if len(self.algorithm_fields[key]) > 2:
                    self.option3_label.setText(f"Additional Option 3: {selected_algorithm[2]['text']}")
                    self.alg_opt3 = json.loads(selected_algorithm[2]['options'])
                    # Sorting the dictionary by key
                    sorted_data = {k: v for k, v in sorted(self.alg_opt3.items())}
                    value = sorted_data.values()
                    # Adding items to the combobox
                    self.option3_combo.addItems(value)
                break

    def on_change_option1(self, index):
        # Getting the selected text
        selected_item = self.option1_combo.currentText()
        # Finding the corresponding key for the selected value
        for key, value in self.alg_opt1.items():
            if value == selected_item:
                self.selected_opt1 = key
                break

    def on_change_option2(self, index):
        # Getting the selected text
        selected_item = self.option2_combo.currentText()
        # Finding the corresponding key for the selected value
        for key, value in self.alg_opt2.items():
            if value == selected_item:
                self.selected_opt2 = key
                break

    def on_change_option3(self, index):
        # Getting the selected text
        selected_item = self.option3_combo.currentText()
        # Finding the corresponding key for the selected value
        for key, value in self.alg_opt3.items():
            if value == selected_item:
                self.selected_opt3 = key
                break

    def select_output_dir(self):
        # Opening a dialog to select a directory
        self.output_dir = QFileDialog.getExistingDirectory(self, "Select Folder to Save")
        self.output_dir_label.setText(f"Output Dir: {self.output_dir}")

    def process_separation(self):
        global path_hash_dict, start_result, separation_n
        for key, value in self.data.items():
            if value == self.type_combo.currentText():
                self.selected_key = key
                break
        separation_type = self.selected_key
        api_token = self.api_input.text()
        option1 = self.selected_opt1
        option2 = self.selected_opt2
        option3 = self.selected_opt3
        path = self.selected_file

        # Clearing field styles before validation
        self.clear_styles()
        # Validation
        if not path:  # If no file is selected
            self.file_button.setStyleSheet(
                "background-color: red; font-size: 18px; padding: 20px; min-width: 300px;")  # Highlighting the button in red
        if not api_token:  # If API token is empty
            self.api_input.setStyleSheet("border: 2px solid red; font-size: 18px; padding: 15px; min-width: 300px;")
        else:
            # Save to file
            with open(self.token_filename, "w") as f:
                f.write(api_token)

        if not separation_type:  # If separation type is not selected
            self.type_combo.setStyleSheet(f"border: 2px solid red; {combo_style}")

        # Check: if there are errors, do not continue the process
        if (path == None) or not api_token or not separation_type:
            os.system('cls')
            print("Error separation:")
            print(f"path: {path}")
            print(f"api_token: {api_token}")
            print(f"separation_type: {separation_type}")
            return

        # Trying to start separation (e.g., generate a hash or error)
        result = self.start_separation(separation_type, api_token, option1, option2, option3, path)
        if 'hash' in result:
            # Connecting the separation progress check thread
            path_hash_dict[result["hash"]] = self.output_dir
            start_result = result
            separation_n += 1
            self.create_button.setText(f"Create Separation: [{separation_n} in progress]")
            self.st = SepThread(self)
            self.st.stop_separation_signal.connect(self.stop_separation)
            self.st.hash = result["hash"]
            self.st.start()
            QMessageBox.information(self, "Result", f"Thread #{separation_n}\nin progress")

    def stop_separation(self, result_text):
        global separation_n
        # Completion of separation
        QMessageBox.information(self, "Result", result_text)
        self.create_button.setText(f"Create Separation: [{separation_n}]")

    def clear_styles(self):
        # Resetting styles
        self.file_button.setStyleSheet(button_style)
        self.api_input.setStyleSheet(input_style)
        self.type_combo.setStyleSheet(combo_style)

    def start_separation(self, separation_type, api_token, option1, option2, option3, path):
        hash, status_code = create_separation(path, api_token, separation_type, option1, option2, option3)
        if status_code == 200:
            return {"success": True, "hash": hash}  # Success with hash
        else:
            return {"success": False, "error": hash}

    def show_separation_types(self):
        # Creating a form to display separation types
        separation_dialog = QDialog(self)
        separation_dialog.setWindowTitle("Separation Types")

        # Getting and sorting data
        self.data = get_separation_types()
        sorted_data = {k: v for k, v in sorted(self.data.items())}

        # Creating QScrollArea for scrolling
        scroll_area = QScrollArea(separation_dialog)
        scroll_area.setWidgetResizable(True)

        # Creating a container for QLabel to use it in ScrollArea
        label_widget = QWidget()
        label_layout = QVBoxLayout(label_widget)

        # Forming data rows and adding them to the layout as QLabel
        for key, value in sorted_data.items():
            label = QLabel(f"{key}: {value}", label_widget)
            label.setStyleSheet(label_style)  # Applying the text style
            label_layout.addWidget(label)

        # Setting the QLabel container in ScrollArea
        scroll_area.setWidget(label_widget)

        # Creating a button to close the form
        close_button = QPushButton("Close", separation_dialog)
        close_button.setStyleSheet(button_style)  # Applying the button style
        close_button.clicked.connect(separation_dialog.accept)

        # Creating the main layout and adding ScrollArea and a button to it
        layout = QVBoxLayout(separation_dialog)
        layout.addWidget(scroll_area)
        layout.addWidget(close_button)

        # Setting the layout in the dialog window
        separation_dialog.setLayout(layout)

        # Displaying the dialog window
        separation_dialog.exec()

    def show_get_result(self):
        dialog = GetResultDialog(self)
        dialog.exec()


class GetResultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Get Separation Result")
        self.setGeometry(150, 150, 400, 200)

        layout = QVBoxLayout()

        # Label and field for hash input
        self.hash_label = QLabel("Enter Hash")
        self.hash_input = QLineEdit()
        self.hash_input.setPlaceholderText("Enter the hash to check")
        self.hash_input.setStyleSheet(input_style)
        layout.addWidget(self.hash_label)
        layout.addWidget(self.hash_input)

        # Check button
        self.check_button = QPushButton("Check")
        self.check_button.setStyleSheet(button_style)
        self.check_button.clicked.connect(self.check_hash)
        layout.addWidget(self.check_button)

        self.setLayout(layout)

    def check_hash(self):
        # Getting the entered hash
        hash_value = self.hash_input.text().strip()

        if not hash_value:
            QMessageBox.warning(self, "Input Error", "Please enter a valid hash.")
            return

        # Checking the hash status
        result = self.check_status(hash_value)

        # If the status is successful, open a dialog to select a folder
        if result["success"]:
            folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Save")
            if folder_path:
                # Getting the result
                result_text = get_result(hash_value, folder_path)
                if result_text != "":
                    # Displaying the text result in the dialog
                    self.show_result(result_text)
        else:
            # If an error occurred, show a message
            QMessageBox.warning(self, "Error", "An error occurred while retrieving file data.")

    def check_status(self, hash_value):
        success, data = check_result(hash_value)
        return {"success": success}  # Successful result

    def show_result(self, result_text):
        # Showing the result in a new window with text
        QMessageBox.information(self, "Result", result_text)


class ResultDialog(QDialog):
    def __init__(self, parent, result):
        super().__init__(parent)
        self.setWindowTitle("Separation Result")
        self.setGeometry(150, 150, 400, 200)
        layout = QVBoxLayout()

        if result["success"]:
            # If successful result, show the hash
            self.result_label = QLabel(f"Separation Successful!\nHash: {result['hash']}")
            self.result_label.setStyleSheet(label_style)
            self.result_input = QLineEdit(result['hash'])
            self.result_input.setStyleSheet(input_style)
            self.result_input.setReadOnly(True)  # Making the field read-only
            layout.addWidget(self.result_label)
            layout.addWidget(self.result_input)
        else:
            # If error, show an error message
            self.result_label = QLabel(f"Error: {result['error']}")
            layout.addWidget(self.result_label)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())