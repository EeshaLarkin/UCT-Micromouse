% =========================================================================
% UCT Micromouse - Student Virtual Testbed
% =========================================================================
% Run this script to spawn a virtual maze and start the simulation server.
% Once it says "Waiting for connection...", click 'Run' in your 
% StudentTemplate.slx model to steer the virtual mouse!
% =========================================================================

% 1. Setup paths to access the simulator tools
script_dir = fileparts(mfilename('fullpath'));
proj_root = fileparts(fileparts(script_dir));

fid = fopen(fullfile(proj_root, 'build', 'matlab_callbacks.log'), 'a');
if fid ~= -1
    fprintf(fid, '%s: StartFcn (launch_virtual_testbed) triggered\n', datestr(now));
    fclose(fid);
end

addpath(fullfile(proj_root, 'matlab', 'simulator'));


% 2. Generate a fresh maze in the base workspace
disp('>> [Testbed] Generating Practice Maze...');
assignin('base', 'maze_data', mm_amaze());

if exist('simstruct_init', 'file')
    evalin('base', 'simstruct_init(0);');
end

% 3. Launch the Python Physics Simulator on Port 8000 if not already running
if ispc
    % On Windows, kill lingering physics_sim.py processes via PowerShell
    [~, ~] = system('powershell -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like ''%physics_sim.py%''\" | Invoke-CimMethod -MethodName Terminate" >nul 2>&1');
    pause(0.2); % Give the OS a moment to release the port
else
    % On macOS/Linux, kill any lingering simulator processes to free up port 8000
    [~, ~] = system('/usr/bin/pkill -f ''[p]hysics_sim.py''');
    pause(0.2); % Give the OS a moment to release the port
end

disp('>> [Testbed] Checking if Python Physics Simulator is already running on port 8000...');
simulator_running = false;
if ispc
    % On Windows, check running processes using PowerShell to avoid socket connect bugs
    [status, cmdout] = system('powershell -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like ''%physics_sim.py%''\""');
    if status == 0 && ~isempty(strfind(cmdout, 'physics_sim.py'))
        simulator_running = true;
    end
else
    % On macOS/Linux, check running processes instead of connecting to the port.
    % Connecting and closing on port 8000 immediately kills the single-connection Python simulator!
    [status, ~] = system('/usr/bin/pgrep -f ''[p]hysics_sim.py''');
    if status == 0
        simulator_running = true;
    end
end

if simulator_running
    disp('>> [Testbed] Simulator is already running. Reusing existing instance.');
end

if ~simulator_running
    disp('>> [Testbed] Spawning Python Physics Simulator in background...');
    python_sim_script = fullfile(proj_root, 'tools', 'physics_sim.py');

    if exist(python_sim_script, 'file')
        log_file = fullfile(proj_root, 'sim_background.log');
        if ismac
            % macOS background execution (clearing DYLD variables to avoid library conflicts)
            cmd = sprintf('env -u DYLD_LIBRARY_PATH -u DYLD_INSERT_LIBRARIES -u DYLD_FRAMEWORK_PATH python3 "%s" > "%s" 2>&1 &', python_sim_script, log_file);
        elseif ispc
            % Windows background execution
            cmd = sprintf('start /B python "%s" &', python_sim_script);
        else
            % Linux background execution (logging output to sim_background.log)
            cmd = sprintf('python3 "%s" > "%s" 2>&1 &', python_sim_script, log_file);
        end
        status = system(cmd);
        if status ~= 0
            disp('[Warning] Failed to auto-start Python simulator.');
            disp(['Please run manually in terminal: python3 ', python_sim_script]);
        end
        pause(1.0); % Give the simulator a moment to bind to the port
    else
        disp('[Warning] Python simulator not found. Falling back to Simulink TCP server...');
        run_tcp_autograder('mm_betterrobot', inf);
    end
end