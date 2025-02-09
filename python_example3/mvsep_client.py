import os
import time
import requests
from requests.exceptions import RequestException
from typing import Dict, List, Optional, Union
import json
import argparse


class MVSEPClient:
    def __init__(self, api_key: str, retries: int = 30, retry_interval: int = 20, debug: bool = True):
        self.api_key = api_key
        self.retries = retries
        self.retry_interval = retry_interval
        self.base_url = "https://mvsep.com/api"
        self.headers = {"User-Agent": "MVSEP Python Client/0.1"}
        self.debug = debug

    def _log_debug(self, message: str) -> None:
        """Helper method for debug logging"""
        if self.debug:
            print(f"[DEBUG] {message}")

    def _make_request(self, method: str, endpoint: str, 
                    params: Optional[Dict] = None, data: Optional[Dict] = None,
                    files: Optional[Dict] = None, stream: bool = False) -> requests.Response:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        self._log_debug(f"Making {method} request to {url}")
        self._log_debug(f"Params: {params}")
        self._log_debug(f"Data: {data}")
        if files:
            self._log_debug(f"Files: {list(files.keys())} (content not logged)")
        
        for attempt in range(self.retries + 1):
            try:
                response = requests.request(
                    method, url,
                    params=params,
                    data=data,
                    files=files,
                    headers=self.headers,
                    stream=stream,
                    timeout=(600, 1200)
                )
                
                self._log_debug(f"Response status: {response.status_code}")
                self._log_debug(f"Response headers: {dict(response.headers)}")
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self.retry_interval))
                    self._log_debug(f"Rate limited, retrying after {retry_after}s")
                    time.sleep(retry_after)
                    continue
                if response.status_code == 400:
                    #print(response)
                    time.sleep(self.retry_interval)
                    continue
                if 500 <= response.status_code < 600 and attempt < self.retries:
                    self._log_debug(f"Server error {response.status_code}, retrying...")
                    time.sleep(self.retry_interval)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError as e:
                self._log_debug(f"HTTP error: {str(e)}")
                if e.response.status_code // 100 == 4 and e.response.status_code != 429:
                    raise
                if attempt == self.retries:
                    raise
                time.sleep(self.retry_interval)
            except RequestException as e:
                self._log_debug(f"Request exception: {str(e)}")
                if attempt == self.retries:
                    raise Exception(f"Request failed after {self.retries} retries: {str(e)}")
                time.sleep(self.retry_interval)
        raise Exception("Unexpected error in request handling")

    # Core Separation Functions (updated with debug logs)
    def create_separation(self, file_path: Optional[str] = None, url: Optional[str] = None,
                        sep_type: int = 11, add_opt1: Optional[Union[str, int]] = None,
                        add_opt2: Optional[Union[str, int]] = None, add_opt3: Optional[Union[str, int]] = None,
                        output_format: int = 0, is_demo: bool = False,
                        remote_type: Optional[str] = None) -> Dict:
        self._log_debug(f"Creating separation with params: sep_type={sep_type}, output_format={output_format}")
        
        data = {
            "api_token": self.api_key,
            "sep_type": str(sep_type),
            "output_format": str(output_format),
            "is_demo": "1" if is_demo else "0"
        }
        files = {}
        
        if file_path and url:
            raise ValueError("Cannot specify both file_path and url")
        if file_path:
            self._log_debug(f"Uploading local file: {file_path}")
            files["audiofile"] = open(file_path, "rb")
        elif url:
            self._log_debug(f"Processing remote URL: {url}")
            data["url"] = url
            if remote_type:
                data["remote_type"] = remote_type
        else:
            raise ValueError("Either file_path or url must be provided")
        
        for opt, val in [("add_opt1", add_opt1), ("add_opt2", add_opt2), ("add_opt3", add_opt3)]:
            if val is not None:
                data[opt] = str(val)
        
        response = self._make_request("POST", "separation/create", data=data, files=files)
        json_response = response.json()
        self._log_debug(f"Create separation response: {json_response}")
        return json_response

    def get_separation_status(self, task_hash: str, mirror: int = 0) -> Dict:
        self._log_debug(f"Getting status for hash: {task_hash}, mirror={mirror}")
        params = {"hash": task_hash, "mirror": str(mirror)}
        if mirror == 1:
            params["api_token"] = self.api_key
        response = self._make_request("GET", "separation/get", params=params)
        json_response = response.json()
        self._log_debug(f"Status response: {json_response}")
        return json_response

    def download_track(self, url: str, output_path: str) -> None:
        """Download a track directly using the full URL from the API response"""
        self._log_debug(f"Downloading track directly from {url}")
        
        # Bypass the base URL since we have full download URLs
        response = requests.get(url, stream=True, headers=self.headers)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        self._log_debug(f"Finished downloading to {output_path}")


    # Updated process_directory with debug logs
    def process_directory(self, input_dir: str, output_dir: str, **kwargs) -> None:
        self._log_debug(f"Processing directory: {input_dir} -> {output_dir}")
        supported_ext = [".mp3", ".wav", ".flac"]
        os.makedirs(output_dir, exist_ok=True)
        filtered_files = os.listdir(input_dir)

        for filename in filtered_files:
            if os.path.splitext(filename)[1].lower() not in supported_ext:
                self._log_debug(f"Skipping unsupported file: {filename}")
                continue
            
            file_path = os.path.join(input_dir, filename)
            self._log_debug(f"Processing {filename}")
            
            try:
                create_resp = self.create_separation(file_path=file_path, **kwargs)
                if not create_resp.get("success"):
                    self._log_debug(f"Creation failed response: {create_resp}")
                    continue
                
                task_hash = create_resp["data"]["hash"]
                self._log_debug(f"Created separation task: {task_hash}")
                
                while True:
                    status_resp = self.get_separation_status(task_hash)
                    self._log_debug(f"Status poll response: {status_resp}")
                    
                    status = status_resp.get("status")
                    if status == "done":
                        self._log_debug("Processing completed successfully")
                        break
                    if status in ["failed", "error"]:
                        self._log_debug("Processing failed")
                        break
                    if status in ["waiting", "processing", "distributing", "merging"]:
                        self._log_debug(f"Current status: {status}, waiting {self.retry_interval}s")
                        time.sleep(self.retry_interval)
                    else:
                        self._log_debug(f"Unknown status: {status}")
                        break
                
                if status != "done":
                    continue
                
                # FIXED: Use 'download' key instead of 'name'
                for file_info in status_resp["data"]["files"]:
                    output_filename = file_info.get("download", f"unknown_{time.time()}.mp3")
                    output_path = os.path.join(output_dir, output_filename)
                    self._log_debug(f"Downloading {output_filename}")
                    # FIXED: Use 'url' key instead of 'link'
                    self.download_track(file_info["url"], output_path)
            
            except Exception as e:
                self._log_debug(f"Exception during processing: {str(e)}")
                print(f"Error processing {filename}: {str(e)}")

    # Updated get_algorithms with debug logs
    def get_algorithms(self) -> Dict:
        self._log_debug("Fetching algorithm list")
        response = self._make_request("GET", "app/algorithms")
        sorted_algos = sorted(response.json(), key=lambda algo: algo['render_id'])
        algo_dict = {}

        for algo in sorted_algos:
            s1 = f"\nID:{algo['render_id']} - {algo['name']}"
            algo_dict[algo['render_id']] = s1 + '\n'
            # print(s1)
            for field in algo['algorithm_fields']:
                s1 = f"\t{field['name']}"
                algo_dict[algo['render_id']] += s1 + '\n'
                # print(s1)
                options = json.loads(field['options'])
                for key, value in sorted(options.items()):
                    s1 = f"\t\t{key}: {value}"
                    algo_dict[algo['render_id']] += s1 + '\n'
                    # print(s1)
        return algo_dict

    # Premium Management
    def enable_premium(self) -> Dict:
        data = {"api_token": self.api_key}
        response = self._make_request("POST", "app/enable_premium", data=data)
        return response.json()

    def disable_premium(self) -> Dict:
        data = {"api_token": self.api_key}
        response = self._make_request("POST", "app/disable_premium", data=data)
        return response.json()

    # Quality Checker
    def create_quality_entry(self, zip_path: str, algo_name: str, main_text: str,
                            dataset_type: int = 0, ensemble: int = 0, password: str = "") -> Dict:
        data = {
            "api_token": self.api_key,
            "algo_name": algo_name,
            "main_text": main_text,
            "dataset_type": str(dataset_type),
            "ensemble": str(ensemble),
            "password": password
        }
        files = {"zipfile": open(zip_path, "rb")}
        response = self._make_request("POST", "quality_checker/add", data=data, files=files)
        return response.json()

    # Additional API Endpoints
    def get_queue_info(self) -> Dict:
        response = self._make_request("GET", "app/queue")
        return response.json()

    def get_news(self, lang: str = "en", start: int = 0, limit: int = 10) -> Dict:
        params = {"lang": lang, "start": start, "limit": limit}
        response = self._make_request("GET", "app/news", params=params)
        return response.json()

    def get_separation_history(self, start: int = 0, limit: int = 10) -> Dict:
        params = {"api_token": self.api_key, "start": start, "limit": limit}
        response = self._make_request("GET", "app/separation_history", params=params)
        return response.json()

    # File Name Preferences
    def enable_long_filenames(self) -> Dict:
        data = {"api_token": self.api_key}
        response = self._make_request("POST", "app/enable_long_filenames", data=data)
        return response.json()

    def disable_long_filenames(self) -> Dict:
        data = {"api_token": self.api_key}
        response = self._make_request("POST", "app/disable_long_filenames", data=data)
        return response.json()


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
    get_types_parser.add_argument('--token', type=str, help="API token for authentication.")

    create_separation_parser = subparsers.add_parser('separate', help="Create a new separation.")
    create_separation_parser.add_argument('--input', type=str, help="Path to the folder where to search files to be separated.")
    create_separation_parser.add_argument('--output_folder', type=str, default="./", help="Path to store the result files.")
    create_separation_parser.add_argument('--token', type=str, help="API token for authentication.")
    create_separation_parser.add_argument('--output_format', type=int, default=1, help="Output format: MP3=0, WAV=1, FLAC=2")
    create_separation_parser.add_argument('--sep_type', type=int, default=20, help="Separation type.")
    create_separation_parser.add_argument('--add_opt1', type=str, default="", help="Additional option 1.")
    create_separation_parser.add_argument('--add_opt2', type=str, default="", help="Additional option 2.")
    create_separation_parser.add_argument('--add_opt3', type=str, default="", help="Additional option 3.")

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args(None)

    # Example Usage
    API_KEY = args.token
    client = MVSEPClient(api_key=API_KEY, debug=True)  # USE DEBUG, ELSE NOTHING WILL BE PRINTED ON TERMINAL, normal prints are not done yet

    if args.command == 'separate':
        algos = client.get_algorithms()
        print('Separate with algorithm: {}'.format(args.sep_type))
        print(algos[args.sep_type])

        # Process directory example / need to check if retries are working correctly !!!
        client.process_directory(
            input_dir = args.input,
            output_dir = args.output_folder,
            output_format = args.output_format,  # MP3=0, WAV=1, FLAC=2
            sep_type = args.sep_type, # use client.get_algorithms() or check documentation details https://mvsep.com/en/full_api for now
            add_opt1 = args.add_opt1, # use client.get_algorithms() or check documentation details https://mvsep.com/en/full_api for now
            add_opt2 = args.add_opt2, # use client.get_algorithms() or check documentation details https://mvsep.com/en/full_api for now
            add_opt3 = args.add_opt3, # use client.get_algorithms() or check documentation details https://mvsep.com/en/full_api for now
        )
    else:
        # Get algos formated list : DONE !
        algos = client.get_algorithms()
        for algo in algos:
            print(algos[algo])

