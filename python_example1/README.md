### Simple example 1

[api_example.py](api_example.py) - this file allows to call 3 different methods:

1) Get list of all possible types of separation:
```bash
python3 api_example.py get_types
```

2) Create separation task with given parameters:
```bash
python3 api_example.py create_separation --input <path/to/file.mp3> --token <your_api_token> --sep_type <separation_type> --add_opt1 <add_opt1> --add_opt2 <add_opt2>
```
Note: `<your_api_token>` is available on MVSep site in your profile. You must have an account. 

For example if you have input.mp3 file located in folder with script you can use this command to separate with **Demucs4 HT (vocals, drums, bass, other)** model with model type: **"htdemucs (Good Quality, Fast)**":
```bash
python3 api_example.py create_separation --input input.mp3 --token DsemTWkdNyChZZWEjnHKVQAcjC543t --sep_type 20 --add_opt1 1 --add_opt2 0
```

This will put file in queue and print hash of file in terminal. After you can use this hash to download separated files.
Example of output: `Hash: 20250131145833-a0bb276157-mixture.wav Return code: 200`

3) Download result of separation
```bash
python3 api_example.py get_result --hash <hash from create_separation> --output_path <path where to store the files>
```
Note: `--output_path` is optional, if you don't set it files will be stored in current directory.

For example if you want to download files from previous step you can use this command:
```bash
python3 api_example.py get_result --hash 20250128141843-f0bb276157-mixture.wav
```

### Run without python on Windows

We create [exe version](api_example_win.exe) which can be run on Windows without python installed. To run just replace `python3 api_example.py` on `api_example_win.exe`. For example:

```bash
api_example_win.exe get_types
```