import os
import sys
import json
import requests
import argparse
import time
import glob
from typing import Union


def create_separation(file, args):
    files = {
        'audiofile': open(file, 'rb'),
        'api_token': (None, args.token),
        'sep_type': (None, args.sep_type),
        'add_opt1': (None, args.add_opt1),
        'add_opt2': (None, args.add_opt2),
        'output_format': (None, '1'),
        'is_demo': (None, '1'),
    }

    response = requests.post('https://mvsep.com/api/separation/create', files=files)
    string_response = response.content.decode('utf-8')
    parsed_json = json.loads(string_response)
    hash = parsed_json["data"]["hash"]

    return hash, response.status_code


def download_file(url, filename, save_path):
    """
    Download the file from the specified URL and save it in the specified path.
    """
    response = requests.get(url)

    if response.status_code == 200:
        output_path = os.path.join(save_path, filename)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        file_size = os.path.getsize(output_path)
        print(f"File '{filename}' have been downloaded successfully! Size: {file_size/ (1024*1024):.2f} MB")
        return True
    else:
        print(f"There was an error loading the file '{filename}'. Status code: {response.status_code}.")
        return False


def get_result(hash, args):
    params = {'hash': hash}
    save_path = args.output_path
    response = requests.get('https://mvsep.com/api/separation/get', params=params)
    data = json.loads(response.content.decode('utf-8'))

    if data['success']:
        try:
            files = data['data']['files']
        except:
            # print("The separation is not ready yet")
            return None
        os.makedirs(save_path, exist_ok=True)
        print("\nFiles to download: {}".format(len(files)))
        for file_info in files:
            url = file_info['url'].replace('\\/', '/')
            filename = file_info['download']
            status = download_file(url, filename, save_path)
        if status:
            return True
        else:
            return False
    else:
        print("An error occurred while retrieving file data.")
        return False


def get_separation_types():
    api_url = 'https://mvsep.com/api/app/algorithms'
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()

        for algorithm in data:
            render_id = algorithm['render_id']
            name = algorithm['name']
            algorithm_group_id = algorithm['algorithm_group_id']

            algorithm_fields = algorithm['algorithm_fields']
            for field in algorithm_fields:
                field_name = field['name']
                field_text = field['text']
                field_options = field['options']

            algorithm_descriptions = algorithm['algorithm_descriptions']
            for description in algorithm_descriptions:
                short_desc = description['short_description']
                # long_desc = description['long_description']
                lang = description['lang']

            print(f"{render_id}: {name}, Group ID: {algorithm_group_id}")
            print(f"\tField Name: {field_name}, Field Text: {field_text}, Options: {field_options}")
            # print(f"\tShort Description: {short_desc}, Long Description: {long_desc}, Language: {lang}\n")
    else:
        print(f"Request failed with status code: {response.status_code}")


def parse_args(dict_args: Union[dict, None]) -> argparse.Namespace:
    """
    Parse command-line arguments for configuring the model, dataset, and training parameters.

    Args:
        dict_args: Dict of command-line arguments. If None, arguments will be parsed from sys.argv.

    Returns:
        Namespace object containing parsed arguments and their values.
    """
    parser = argparse.ArgumentParser(description="Console application for managing MVSEP separations.")
    subparsers = parser.add_subparsers(dest='command')

    get_types_parser = subparsers.add_parser('get_types', help="Get available separation types.")

    create_separation_parser = subparsers.add_parser('separate', help="Create a new separation.")
    create_separation_parser.add_argument('--input', type=str, help="Path to the folder where to search files to be separated.")
    create_separation_parser.add_argument('--output_path', type=str, default="./", help="Path to store the result files.")
    create_separation_parser.add_argument('--token', type=str, help="API token for authentication.")
    create_separation_parser.add_argument('--sep_type', type=str, help="Separation type.")
    create_separation_parser.add_argument('--add_opt1', type=str, default="", help="Additional option 1.")
    create_separation_parser.add_argument('--add_opt2', type=str, default="", help="Additional option 2.")

    if dict_args is not None:
        args = parser.parse_args([])
        args_dict = vars(args)
        args_dict.update(dict_args)
        args = argparse.Namespace(**args_dict)
    else:
        args = parser.parse_args()

    return args


def wait_to_response(hash, args):
    print("Wait while file will be processed on server", end='')
    counter = 0
    while counter < 360:
        response = get_result(hash, args)
        if response:
            break
        else:
            counter += 1
            print('...', end='')
            time.sleep(10)


def main():
    if len(sys.argv) > 1:
        args = parse_args(None)
        if args.command == 'create_separation':
            if not os.path.isdir(args.input):
                print('--input parameter must be a directory!')
                exit()
            files = []
            for extension in ['wav', 'flac', 'mp3']:
                files += glob.glob(os.path.join(args.input) + '/*.{}'.format(extension))
            print('Found files to process: {}'.format(len(files)))
            for file in files:
                print('Create separation task for file: {}'.format(file))
                res = create_separation(file, args)
                if len(res) == 2:
                    hash, return_code = res
                    print('Hash: {} Return code: {}'.format(hash, return_code))
                else:
                    print('Problem with separation', res)
                    continue
                wait_to_response(hash, args)

        if args.command == 'get_types':
            get_separation_types()
    else:
        print("No arguments provided. Please provide command-line arguments.")


if __name__ == "__main__":
    main()