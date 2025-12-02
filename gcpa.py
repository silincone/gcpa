import re
import sys
import argparse
from pathlib import Path
from enum import Enum

UNIT_TO_NS = {
    'ns': 1.0,
    'us': 1_000.0,
    'ms': 1_000_000.0,
    's': 1_000_000_000.0
}

class ModuleValues(Enum):
    Design = 0
    Source = 1
    Destination = 2
    Data_Path_Delay = 3
    Critical_Path = 4
    Slack = 5


def toNanoSeconds(time_pair):
    value, unit = time_pair

    factor = UNIT_TO_NS.get(unit.lower(), None)

    if factor is None:
        raise ValueError(f"[ERROR] Unkown unit '{unit}'.\n\tSupported units are: {list(UNIT_TO_NS.keys())}")
    
    return value * factor

def validateFile(filePath):
    path_obj = Path(filePath)

    if not path_obj.exists():
        print(f"[ERROR] '{filePath}' does not exist.")
        return False
    
    if not path_obj.suffix.lower() == '.txt':
        print(f"[ERROR] '{filePath}' is not a .txt file.")
        return False

    print(f"[INFO] Found '{filePath}'.")
    return True

def parseDesignName(f):
    for line in f:
        if "Design" in line and ":" in line:
            parts = line.split(':', 1)

            if "Design" in parts[0]:
                return parts[1].strip()
                
def parseCriticalPath(f):
    for line in f:
        if "Data Path Delay" in line and ":" in line:
            parts = line.split(':', 1)

            if "Data Path Delay" in parts[0]:
                _criticalPath_str = parts[1].split()[0]

                match = re.match(r"([\d\.]+)([a-zA-Z]+)", _criticalPath_str)

                if match:
                    value_str, unit = match.groups()
                    return [float(value_str), unit]

def parseSlack(f):
    slack = {}
    
    for line in f:
        if line is not None:
            if "Source" in line and ":" in line:
                parts = line.split(':', 1)

                if "Source" in parts[0]:
                    slack[ModuleValues.Source] = parts[1].strip()
                    break

    for line in f:
        if line is not None:
            if "Destination" in line and ":" in line:
                parts = line.split(':', 1)

                if "Destination" in parts[0]:
                    slack[ModuleValues.Destination] = parts[1].strip()
                    break

    for line in f:
        if line is not None:
            if "Data Path Delay" in line and ":" in line:
                parts = line.split(':', 1)

                if "Data Path Delay" in parts[0]:
                    _pathDelay_str = parts[1].split()[0]

                match = re.match(r"([\d\.]+)([a-zA-Z]+)", _pathDelay_str)

                if match:
                    value_str, unit = match.groups()
                    slack[ModuleValues.Data_Path_Delay] = [float(value_str), unit]
                    break
    
    return slack

def parseFile(filePath, onlyCriticalPath):
    with open(filePath, 'r') as f:
        module = {}
        slacks = []
        
        _startPointForSlacks = f.tell()

        module[ModuleValues.Design] = parseDesignName(f)
        module[ModuleValues.Critical_Path] = parseCriticalPath(f)
        
        if onlyCriticalPath:
            return module
        
        f.seek(_startPointForSlacks)
        for line in f:
            if "Slack:" in line:
                slacks.append(parseSlack(f))
        
    module[ModuleValues.Slack] = slacks
    timings = []

    for slack in slacks:
        timings.append(slack[ModuleValues.Data_Path_Delay])
    try:
        _criticalPath = max(timings, key=toNanoSeconds)
    except ValueError as e:
        print(e)
        sys.exit(1)
    if not module[ModuleValues.Critical_Path] == _criticalPath:
        module[ModuleValues.Critical_Path] = _criticalPath

    return module


def main():
    modules = {}
    timings = []

    parser = argparse.ArgumentParser(description="gcpa: Global Critical Path delay Analyzer.")

    parser.add_argument('files', nargs='+', help='List of timing files (.txt) to process.')

    args = parser.parse_args()

    for filePath in args.files:
        if validateFile(filePath):
            onlyCriticalPath = False
            
            _value = parseFile(filePath, onlyCriticalPath=onlyCriticalPath)

            modules[_value.get(ModuleValues.Design)] = _value
        else:
            sys.exit(1)
    
    print(100 * '-')
    for key, value in modules.items():
        timings.append(value.get(ModuleValues.Critical_Path))

        _cricitalPath_str = f"{value.get(ModuleValues.Critical_Path)[0]}{value.get(ModuleValues.Critical_Path)[1]}"
        print(f"Block: '{key}',\nMax Path Delay: {_cricitalPath_str}\n")

    try:
        _globalCriticalPath = max(timings, key=toNanoSeconds)
    except ValueError as e:
        print(e)
        sys.exit(1)

    print(100 * '-')
    if _globalCriticalPath:
        for key, value in modules.items():
            if value[ModuleValues.Critical_Path] == _globalCriticalPath:
                _globalCriticalPath_str = f"{_globalCriticalPath[0]}{_globalCriticalPath[1]}"
                print(f"Global Critical Path Block: '{key}', with Critical Path Delay: {_globalCriticalPath_str}")
 
if __name__ == "__main__":
    main()
