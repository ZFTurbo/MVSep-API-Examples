### Simple example 2

[api_example2.py](python_example2/api_example2.py) - this file allows to call 2 different methods:

1) Get list of all possible types of separation:
```bash
python3 api_example2.py get_types
```

2) Create separation task with given parameters:
```bash
python3 api_example2.py separate --input <path/to/folder/with/audio/files> --output_path <path where to store the files> --token <your_api_token> --sep_type <separation_type> --add_opt1 <add_opt1> --add_opt2 <add_opt2>
```
Note: `<your_api_token>` is available on MVSep site in your profile. You must have an account. 

For example if you have `input.mp3`, `input2.mp3` files located in folder `audio` in current directory you can use this command to separate with **MelBand Roformer (vocals, instrumental)** model with model type: **ver 2024.08 (SDR vocals: 11.17, SDR instrum: 17.48)**":
```bash
python3 api_example2.py separate --input "./audio/" --token DsemTWkdNyChZZWEjnHKVQAcjC543t --sep_type 48 --add_opt1 1
```
It will automatically put files in queue and download them when they are ready.