% =========================================================================
% UCT Micromouse - Milestone 1 Autograder (The Square Run)
% =========================================================================
% Evaluates the student's closed-loop control system by commanding a
% 1.0m x 1.0m square path and scoring the final return-to-start accuracy.
% Perturbs physical parameters (asymmetric gains, wheel slip) to ensure
% feedback design (IMU + encoders) is active.
% =========================================================================

% 1. Configure Paths to ensure the Autograder can see the Simulator/Mazes
script_dir = fileparts(mfilename('fullpath'));
tasks_dir = fileparts(script_dir);
autograder_dir = fileparts(tasks_dir);
matlab_dir = fileparts(autograder_dir);
root_dir = fileparts(matlab_dir);

addpath(autograder_dir);                           % For run_tcp_autograder
addpath(fullfile(autograder_dir, 'mazes'));        % For mm_emptymaze
addpath(fullfile(matlab_dir, 'simulator'));        % For physics engine & simstruct_init
addpath(matlab_dir);                               % For scripts/data paths

% 2. Generate the Virtual Environment (Clean empty arena)
disp('>> [Milestone 1] Generating Boundary-Only Arena...');
maze_data = mm_emptymaze(); 
assignin('base', 'maze_data', maze_data); 

% 3. Initialize Base Workspace Parameters
if exist('simstruct_init', 'file')
    try
        evalin('base', 'simstruct_init(0);');
    catch ME_INIT
        disp(['[Warning] simstruct_init failed: ', ME_INIT.message]);
        evalin('base', 'simstruct = struct();');
    end
else
    evalin('base', 'simstruct = struct();');
end

if exist('simstructlocal_init', 'file')
    evalin('base', 'simstruct = simstructlocal_init(simstruct);');
end

% --- ADVERSARIAL TESTING: INJECT PERTURBATIONS & WHEEL SLIP ---
disp('>> [Milestone 1] Injecting motor imbalance and wheel slip parameters...');

% Left wheel is slightly weaker, Right wheel is slightly stronger
evalin('base', 'simstruct.motor_gain_L = 0.94;'); 
evalin('base', 'simstruct.motor_gain_R = 1.04;');

% Inject wheel slip / traction loss coefficient (reduces effective forward traction forces)
evalin('base', 'simstruct.wheel_slip_coefficient = 0.08;'); 

% Inject minor sensor noise and bias to test Kalman/Gyro integration
evalin('base', 'simstruct.gyro_bias = 0.02;'); % deg/s drift
evalin('base', 'simstruct.sensor_noise_std = 0.05;');

% 4. Launch the TCP Server using your legacy physics model
disp('>> [Milestone 1] Launching Simulation Server on Port 8000...');
physics_model = 'mm_betterrobot'; 

% Run the autograder with a 45.0 second time limit to complete the 4-meter path
[trajectory, status] = run_tcp_autograder(physics_model, 45.0);

% 5. Evaluate the Student's Run
disp(['>> [Milestone 1] Session Finished with status: ', status]);

if ~isempty(trajectory)
    % trajectory array format: [Time, X, Y, Theta]
    start_x = trajectory(1, 2);
    start_y = trajectory(1, 3);
    final_x = trajectory(end, 2);
    final_y = trajectory(end, 3);
    
    % Compute Euclidean error from starting position
    d_e = sqrt((final_x - start_x)^2 + (final_y - start_y)^2);
    
    % Check if the mouse actually attempted to drive (max displacement from start)
    disp_log = sqrt((trajectory(:, 2) - start_x).^2 + (trajectory(:, 3) - start_y).^2);
    max_displacement = max(disp_log);
    
    disp('=== Evaluation Results ===');
    disp(['Start position    : (', num2str(start_x), ', ', num2str(start_y), ')']);
    disp(['Final position    : (', num2str(final_x), ', ', num2str(final_y), ')']);
    disp(['Max Displacement  : ', num2str(max_displacement), ' m']);
    disp(['Final Return Error: ', num2str(d_e * 100), ' cm']);
    
    if max_displacement < 0.20
        % The mouse barely moved (less than 20cm). Probably a compile error or timeout without starting.
        grade = 0;
        disp('GRADE: 0% - Mouse did not complete the square run or fail to move.');
    else
        % Continuous Grading Curve:
        % - Error <= 5cm           -> 100%
        % - Error between 5-15cm   -> Tapers from 100% down to 85%
        % - Error between 15-30cm  -> Tapers from 85% down to 60% (baseline pass)
        % - Error > 30cm           -> Tapers from 60% down to 0% at 1.0m
        if d_e <= 0.05
            grade = 100;
        elseif d_e <= 0.15
            grade = 100 - (100 - 85) * (d_e - 0.05) / (0.15 - 0.05);
        elseif d_e <= 0.30
            grade = 85 - (85 - 60) * (d_e - 0.15) / (0.30 - 0.15);
        else
            grade = max(0, 60 - 60 * (d_e - 0.30) / (1.00 - 0.30));
        end
        
        % Apply minor penalty if they hit the boundary walls (soft collision)
        if strcmp(status, 'Crashed')
            grade = max(0, grade - 15.0); 
            disp('[Evaluation] Applied collision penalty: -15%');
        end
        
        % Apply minor penalty if they timed out (failed to stop on their own)
        if strcmp(status, 'Time Limit Exceeded')
            grade = max(0, grade - 10.0);
            disp('[Evaluation] Applied timeout penalty: -10%');
        end
        
        disp(['GRADE: ', num2str(round(grade)), '%']);
    end
else
    disp('>> ERROR: No trajectory logged. The client did not run.');
    disp('GRADE: 0%');
end