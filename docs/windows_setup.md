# Install flow infrastructure on Windows 10
These instructions follow the particular paths used on the PicoProbe user computer to provide a concrete example. 

**Please update the paths to your own system.**

1. Install git: https://git-scm.com/download/win

2. Open Windows PowerShell and navigate to the software folder
```bash
cd 'E:\PicoProbe User Local Data\Brace\software'
```
3. Identify the correct Python to use (preferably 3.9 or later)
```bash
where.exe python
```
Which outputs:
```console
C:\ProgramData\Miniconda3\python.exe
```

4. Install the source code
```
git clone https://github.com/ramanathanlab/PicoProbeDataFlow.git
cd .\PicoProbeDataFlow\
```

5. Enable the ability to run scripts from PowerShell. See [here](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-7.3) for more information.

This command should be run each time a new PowerShell session is opened if you need to use the session to activate a Python virtual environment:
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

6. Create a virtual environment:
```bash
C:\ProgramData\Miniconda3\python.exe -m venv env
.\env\Scripts\activate
```

7. Checking the python and pip locations should return the new executables in the env\Scripts folder:
```bash
where.exe python
where.exe pip
```
Which outputs
```console
E:\PicoProbe User Local Data\Brace\software\PicoProbeDataFlow\env\Scripts\python.exe
E:\PicoProbe User Local Data\Brace\software\PicoProbeDataFlow\env\Scripts\pip.exe
```

8. Install the package:
```bash
pip install -U setuptools wheel
python -m pip install --upgrade pip
pip install -r .\requirements\windows_requirements.txt
pip install -e .
```

9. Setup the transfer directory using [Globus Connect Personal](https://www.globus.org/globus-connect-personal):

The GlobusEndpoint configured on the User machine is rooted at `C:\`

We will use this directory for our transfers:
```console
C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers
```

Now we have all the software installed.

# Running a Flow

Make sure to activate your virtual environment (for each PowerShell session you open) by running:
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
cd 'E:\PicoProbe User Local Data\Brace\software\PicoProbeDataFlow'
.\env\Scripts\activate
```

## Hyperspectral Imaging Flow

Run the hyperspectral application:
```console
python .\examples\picoprobe_metadata_flow\main.py -c .\examples\picoprobe_metadata_flow\config\windows_picoprobe_to_polaris.yaml -l C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers
```

Okay, now a program is running that is watching the `C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers` directory
for new EMD files to appear. When they appear, it will automatically start a new flow.

Open a separate PowerShell and copy the test files into the transfer directory:
```console
cd 'E:\PicoProbe User Local Data\Brace\software\PicoProbeDataFlow\'
cp .\data\VeloxTest-Membranes.emd C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers
```

You should see a log message appear in the original PowerShell session that is running the watcher. You may need to authenticate Gladier by following the pop-up menu in the browser.

## Spatiotemporal Imaging Flow

Running the spatiotemporal application:
```console
python .\examples\temporal_application\main.py -c .\examples\temporal_application\config\windows_picoprobe_to_polaris_compute.yaml -l C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers
```

Okay, now a program is running that is watching the `C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers` directory
for new EMD files to appear. When they appear, it will automatically start a new flow.

Open a separate PowerShell and copy the test files into the transfer directory:
```console
cd 'E:\PicoProbe User Local Data\Brace\software\PicoProbeDataFlow\'
cp '.\data\2023081040-700kx MultiFrams 991ms 600F Counting & FFI mode Falcon 700 kx 1819.emd' C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers
```

## Using a simulator to start many flows automatically

If the above examples worked, then you can now use a `simulator` program that periodically copies the files to the the transfer directory automatically.

The settings we used for the `Hyperspectral Imaging` production run:
```console
python -m picoprobe.simulator -i .\data\ -o C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers -g Velox*.emd -t 30
```

The settings we used for the `Spatiotemporal Imaging` production run:
```console
python -m picoprobe.simulator -i .\data\ -o C:\Users\PicoProbeUser\Documents\MicroscopeData\Brace\transfers -g 2023*.emd -t 180
```

# Analyzing flow performance results

Follow these instructions to pull logs from Globus containing flow runtime statistics. You will need to use your own flow UUIDs, otherwise, Globus will return a `404 Not Found` error if you are not authenticated. Running the `picoprobe.flow_analyzer` will also output a `performance_<UUID>.pkl` file which can be used to recreate our performance figures in the paper.

Make sure to activate your virtual environment by running:
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
cd 'E:\PicoProbe User Local Data\Brace\software\PicoProbeDataFlow'
.\env\Scripts\activate
```

We will also need the `pandas` package:
```bash
pip install pandas
```

## Hyperspectral Imaging Flow
The name of the flow used for our production run: `PicoProbeMetadataFlow_Production_v2`
The flow UUID: `58175c8f-e94d-4f7e-b272-aff116bf86b3`

This command pulls logs from Globus containing flow runtime statistics:
```console
python -m picoprobe.flow_analyzer -i 58175c8f-e94d-4f7e-b272-aff116bf86b3 -l 200
```

The output:
```bash
https://auth.globus.org/scopes/58175c8f-e94d-4f7e-b272-aff116bf86b3/flow_58175c8f_e94d_4f7e_b272_aff116bf86b3_user
Getting more runs
Getting more runs
Getting more runs
Getting more runs
Getting more runs
43b278d9-7c97-4cc6-85ac-858767f82b8c
782ae71f-dc1d-4a84-ac20-41f5fe54e105
c59a665d-70ba-4306-8987-21f6b28124e9
e6638453-2192-4b1c-9bab-5b254dc12128
f2853310-8a0f-48a4-8c40-9933ba3d3ba6
a3f09991-9073-4f8a-85d4-bf911d4feb56
28d8469d-cc31-457a-af01-503581e76a06
acfb384f-c143-41b3-8be1-37cce955856f
914f4426-2fb6-4276-96e7-57f83fe52a99
f64be9b1-1541-414e-9103-0e19c55ce39c
b092fcc3-8bc9-451c-97b8-4018f328e178
154a345b-358d-4506-9aba-63d508bd1e19
ba92f067-3561-4f0c-8e0c-ffcb20777af6
ad1b289e-1c09-45a9-99f8-04f4a5567c0d
5b5aa949-80fe-4981-a5c8-b0026e908954
bb737dbd-9f34-4c37-9185-848812cf67b5
b37f419b-a054-4bc4-b61d-5f1317c96cb4
64e9c9ca-44be-4305-a03c-d8c2d0bb8de8
37d3c97e-7f3f-458e-b257-c798cc7b114f
be3b3331-70b4-47dc-ae9c-17733d80f31a
5ef8d447-cf67-4f9f-ba75-7869417bdabf
6bc21ff5-3b7c-40be-875a-117608edacdd
d5645bda-be25-4e6c-955a-2ad4de1822e3
c8a42b14-a555-4414-a08e-42f612769f18
ed2ec3c1-e267-4cad-8c4a-7e7f5707546f
517bc8fc-c9f2-4593-9752-b7419790d0f0
38ce7fa6-15b4-4081-9d4a-44279ed96226
568e247e-b4a3-40ed-814b-4b7f9620fff9
2724c2ff-8691-4dc0-966f-63b3d39bd35c
43498b0e-1092-427e-a4fb-b3eae704e85c
fb344d20-a385-4681-a6ee-6c94fb0f6413
7f48a24d-5c72-4165-b84f-cd22290599dc
e56bc574-b910-4e2b-9fde-900d2ead752a
590384e7-a752-49ca-ac18-91f4b3a1c31e
faca5ce8-6b2a-495e-a717-60c81a5a4d5b
2df57825-c7aa-418c-8a6b-e1311e775c04
529badf9-747f-454b-98d0-59730dd46424
4a9b6306-ffa7-48ca-8d6c-5f31d770d563
ff24aa8f-da16-4db6-a362-f14b780bc6b2
c581dad2-d3b9-46ea-964b-91bc2110407b
a27cc9f4-c658-4039-8573-025285642b77
5b9bba7a-7a28-4ba4-9832-befde9b39b4b
4079f2f7-22bf-4bca-b850-7adb6fb168c6
ab808643-a745-4fae-a17f-bf1688079ac4
70bf873c-b18f-41ac-9ceb-f1814db6854d
59f7c668-1576-46f5-b1ca-dad8df09d014
3f114f71-73cf-4201-b598-93f9b37e4d0b
eacea6c5-d6d8-4e41-aba2-e2b17c1abf67
172c69fb-ebb3-4901-943f-c2cb94b82e29
dd9ddaf7-2f43-4cec-ac84-5860242d67ef
5cf2dc6c-487d-4446-9bc4-ca7edd855be1
57002bf3-80d2-4177-91df-dc9f92654b6a
860ac8e6-670f-47d0-af4f-e6c07092b47b
037dbd8e-6ff0-4620-9912-7446abda6c4e
b4e3a51b-546e-40ea-938c-c442c883e1de
459182de-d7f0-48f9-87b5-b2dee8090e7f
26cd7198-00f2-4043-91b8-8e4a4963f39f
a4c16a65-4d50-4817-8742-7ca6f3464843
7829d278-60cb-47c1-bb4c-5603893d550f
c5280b40-a444-42f1-be1d-f5ef1f8f45ad
b3e43318-f148-4646-bf14-8191f88aff7a
e622b7a0-3d6e-4b4f-b959-f55342bd03cc
36c0f2c9-56d9-4524-a130-030faac82a9d
4823ab8a-8d03-4123-bde1-07b10bea7ab2
9d6e13e3-4198-4669-8121-b07dcdce7509
cb532d63-c60e-4d89-908e-fb7c5ec4298e
869359ac-6f80-4239-9c0b-ac12156ec51b
02cca9f4-72b2-4e11-92ee-22daf4ac4865
448415a2-364d-4790-870f-a1329cbc0a36
4117a707-a2cd-423e-9540-e55ffb745293
32e277a3-1206-4cc4-9339-e8b4cf946feb
a1dbe7fc-f2f8-4ed8-9fa1-06adbc9041b2
Found 72 flow runs.
Loaded 72 runs.
Flow:    mean 47s, min 29s, max 181s
Transfer:        mean 19s, median 19s, std 4s, min 11s, max 34s
HyperspectralImageTool:  mean 13s, median 7s, std 26s, min 3s, max 138s
Publishv2GatherMetadata:         mean 6s, median 5s, std 2s, min 3s, max 14s
Publishv2Ingest:         mean 6s, median 5s, std 2s, min 4s, max 16s
Bytes Transferred:       mean 0.089GB, Total 6.424GB
funcX Time:      mean 20s, Total 1444s
```


## Spatiotemporal Imaging Flow
The name of the flow used for our production run: `PicoProbeTemporalImaging_Production_v2`
The flow UUID: `49af5d02-6d4d-4bf9-9666-813a9f2e106f`

This command pulls logs from Globus containing flow runtime statistics:
```console
python -m picoprobe.flow_analyzer -i 49af5d02-6d4d-4bf9-9666-813a9f2e106f -l 200
```

The output:
```bash
https://auth.globus.org/scopes/49af5d02-6d4d-4bf9-9666-813a9f2e106f/flow_49af5d02_6d4d_4bf9_9666_813a9f2e106f_user
0895a642-5eda-4a62-9d4a-c1372a544043
764dba1a-cded-41d8-b766-d6232b0d3404
03e49b55-6620-48ed-bc98-b32d9a532c00
3d058bb2-f7c3-4af3-9ce8-f7de0bb5cc43
c12f06be-7a0e-42df-9bef-0fe24a32dbbf
44adc0a1-3d03-4620-b953-55f600c52fc2
0ef6f15e-94ae-4166-aedb-f0eac28ed962
dc1d7031-7ba1-445e-8bc2-3039e89a29b8
dc06cf50-13e3-4720-9632-eec3cfd30be3
acecc1d2-d007-410f-a3b4-ed39ee113dea
139d3b97-28c8-434b-893a-c082c455ee62
9bdaa0fc-d3dd-409d-8c07-85130505ba61
53b241dd-5099-49cc-9acd-d152782f7540
8907cb91-9357-4387-9ee4-cea87bf600ad
d20a51f0-70a4-4295-bc77-697a2253294a
10bfbe08-c6e4-4d6e-b65c-224e2122e84c
8510d022-5353-4f2c-a817-bb026b0a5f74
595c67d7-f258-49a4-ba65-7307c58320c6
Found 18 flow runs.
Loaded 18 runs.
Flow:    mean 224s, min 195s, max 274s
Transfer:        mean 142s, median 140s, std 8s, min 133s, max 163s
TemporalImageTool:       mean 52s, median 47s, std 14s, min 36s, max 93s
Publishv2GatherMetadata:         mean 20s, median 18s, std 6s, min 11s, max 35s
Publishv2Ingest:         mean 7s, median 5s, std 4s, min 4s, max 22s
Bytes Transferred:       mean 1.206GB, Total 21.716GB
funcX Time:      mean 72s, Total 1305s
```
