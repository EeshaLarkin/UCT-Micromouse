% =========================================================================
% UCT Micromouse - Student Virtual Testbed
% =========================================================================
% Run this script to spawn a virtual maze and start the simulation server.
% Once it says "Waiting for connection...", click 'Run' in your 
% StudentTemplate.slx model to steer the virtual mouse!
% =========================================================================

% 1. Setup paths to access the hidden simulator tools
script_dir = fileparts(mfilename('fullpath'));
root_dir = fileparts(script_dir);

addpath(fullfile(root_dir, 'matlab', 'autograder'));
addpath(fullfile(root_dir, 'matlab', 'autograder', 'mazes'));
addpath(fullfile(root_dir, 'matlab', 'simulator'));

% 2. Generate a fresh maze in the base workspace
disp('>> [Testbed] Generating Practice Maze...');
assignin('base', 'maze_data', mm_amaze());

if exist('simstruct_init', 'file')
    evalin('base', 'simstruct_init(0);');
end

% 3. Launch the Python Physics Simulator on Port 8000 if not already running
disp('>> [Testbed] Checking if Python Physics Simulator is already running on port 8000...');
simulator_running = false;
try
    s = java.net.Socket('127.0.0.1', 8000);
    s.close();
    simulator_running = true;
    disp('>> [Testbed] Simulator is already running. Reusing existing instance.');
catch
    % Connection failed, meaning simulator is not running
end

if ~simulator_running
    disp('>> [Testbed] Spawning Python Physics Simulator in background...');
    python_sim_script = fullfile(root_dir, 'python', 'tools', 'physics_sim.py');

    if exist(python_sim_script, 'file')
        if ispc
            % Windows background execution
            cmd = sprintf('start /B python "%s" &', python_sim_script);
        else
            % macOS/Linux background execution
            cmd = sprintf('python3 "%s" &', python_sim_script);
        end
        status = system(cmd);
        if status ~= 0
            disp('[Warning] Failed to auto-start Python simulator.');
            disp(['Please run manually in terminal: python3 ', python_sim_script]);
        end
        pause(0.5); % Give the simulator a moment to bind to the port
    else
        disp('[Warning] Python simulator not found. Falling back to Simulink TCP server...');
        run_tcp_autograder('mm_betterrobot', inf);
    end
end