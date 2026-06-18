classdef uct_autograder_app < handle
    properties
        UIFigure
        
        % Layout containers
        LoginPanel
        DashboardPanel
        
        % Login UI elements
        StudentIDEditField
        LoginButton
        TitleLabel
        
        % Dashboard UI elements
        WelcomeLabel
        TrackLabel
        TrackDropDown
        UploadButton
        FileStatusLabel
        GradeButton
        ScoreGrid
        
        % Feedback UI elements
        FeedbackAxes
        ReportLabel
        ReportLinkLabel
        StatusLabel
        
        % Administrator view
        PlagiarismFlagLabel
        
        % Database and paths
        SubmissionsDbPath
        GradesCsvPath
        SubmissionsDir
        
        % State variables
        StudentID = ''
        SelectedTrack = 'Simulink Track'
        UploadedFilePath = ''
        SubmissionsDb = struct()
    end
    
    methods
        function app = uct_autograder_app()
            % Constructor - initialize database paths and create UI
            autograder_dir = fileparts(mfilename('fullpath'));
            db_dir = fullfile(autograder_dir, 'db');
            if ~exist(db_dir, 'dir')
                mkdir(db_dir);
            end
            
            app.SubmissionsDbPath = fullfile(db_dir, 'submissions.json');
            app.GradesCsvPath = fullfile(db_dir, 'grades_d2l.csv');
            app.SubmissionsDir = fullfile(db_dir, 'submissions');
            if ~exist(app.SubmissionsDir, 'dir')
                mkdir(app.SubmissionsDir);
            end
            
            % Load submission database
            app.loadDb();
            
            % Setup the UI Figure
            app.createUI();
        end
        
        function delete(app)
            % Clean up figure on deletion
            if ishandle(app.UIFigure)
                delete(app.UIFigure);
            end
        end
    end
    
    methods
        function loadDb(app)
            if exist(app.SubmissionsDbPath, 'file')
                try
                    fid = fopen(app.SubmissionsDbPath, 'r');
                    raw = fread(fid, '*char')';
                    fclose(fid);
                    if ~isempty(raw) && ~strcmp(raw, '{}')
                        app.SubmissionsDb = jsondecode(raw);
                    else
                        app.SubmissionsDb = struct();
                    end
                catch
                    app.SubmissionsDb = struct();
                end
            else
                app.SubmissionsDb = struct();
            end
        end
        
        function saveDb(app)
            try
                fid = fopen(app.SubmissionsDbPath, 'w');
                fwrite(fid, jsonencode(app.SubmissionsDb));
                fclose(fid);
            catch ME
                disp(['[Error] Failed to save submissions database: ', ME.message]);
            end
        end
        
        function createUI(app)
            % Main window
            app.UIFigure = uifigure('Name', 'UCT Micromouse Web Autograder', ...
                'Position', [100 100 850 550], 'Color', [0.12 0.16 0.23]);
            
            % 1. LOGIN SCREEN
            app.LoginPanel = uipanel(app.UIFigure, 'Title', '', ...
                'Position', [225 125 400 300], ...
                'BackgroundColor', [0.2 0.25 0.33], ...
                'ForegroundColor', [0.97 0.98 0.99]);
            
            app.TitleLabel = uilabel(app.LoginPanel, ...
                'Text', 'UCT Micromouse Autograder', ...
                'Position', [20 220 360 40], ...
                'FontSize', 22, 'FontWeight', 'bold', ...
                'FontColor', [0.97 0.98 0.99], 'HorizontalAlignment', 'center');
            
            uilabel(app.LoginPanel, ...
                'Text', 'Enter Student Number:', ...
                'Position', [50 140 300 22], ...
                'FontSize', 14, 'FontColor', [0.97 0.98 0.99]);
            
            app.StudentIDEditField = uieditfield(app.LoginPanel, 'text', ...
                'Position', [50 100 300 30], ...
                'FontSize', 14, 'BackgroundColor', [0.88 0.9 0.94]);
            
            app.LoginButton = uibutton(app.LoginPanel, 'push', ...
                'Text', 'Log In', ...
                'Position', [120 40 160 36], ...
                'FontSize', 14, 'FontWeight', 'bold', ...
                'BackgroundColor', [0.01 0.52 0.78], ...
                'FontColor', [1 1 1], ...
                'ButtonPushedFcn', @(btn, event) app.loginCallback());
            
            % 2. MAIN DASHBOARD PANEL (Initially Hidden)
            app.DashboardPanel = uipanel(app.UIFigure, 'Title', '', ...
                'Position', [25 25 800 500], ...
                'BackgroundColor', [0.2 0.25 0.33], ...
                'ForegroundColor', [0.97 0.98 0.99], ...
                'Visible', 'off');
            
            app.WelcomeLabel = uilabel(app.DashboardPanel, ...
                'Text', 'Welcome, Student', ...
                'Position', [20 450 400 30], ...
                'FontSize', 18, 'FontWeight', 'bold', ...
                'FontColor', [0.97 0.98 0.99]);
            
            app.TrackLabel = uilabel(app.DashboardPanel, ...
                'Text', 'Select Submission Track:', ...
                'Position', [20 390 200 22], ...
                'FontSize', 14, 'FontColor', [0.97 0.98 0.99]);
            
            app.TrackDropDown = uidropdown(app.DashboardPanel, ...
                'Items', {'Simulink Track', 'Python Track'}, ...
                'Position', [20 355 220 30], ...
                'FontSize', 14, ...
                'ValueChangedFcn', @(dd, event) app.trackChangedCallback());
            
            app.UploadButton = uibutton(app.DashboardPanel, 'push', ...
                'Text', 'Upload File (.slx)', ...
                'Position', [20 290 220 36], ...
                'FontSize', 14, 'FontWeight', 'bold', ...
                'BackgroundColor', [0.01 0.52 0.78], ...
                'FontColor', [1 1 1], ...
                'ButtonPushedFcn', @(btn, event) app.uploadFileCallback());
            
            app.FileStatusLabel = uilabel(app.DashboardPanel, ...
                'Text', 'No file uploaded yet.', ...
                'Position', [20 250 250 30], ...
                'FontSize', 12, 'FontColor', [0.8 0.82 0.85]);
            
            app.GradeButton = uibutton(app.DashboardPanel, 'push', ...
                'Text', 'Submit & Grade', ...
                'Position', [20 180 220 45], ...
                'FontSize', 16, 'FontWeight', 'bold', ...
                'BackgroundColor', [0.06 0.73 0.51], ...
                'FontColor', [1 1 1], ...
                'Enable', 'off', ...
                'ButtonPushedFcn', @(btn, event) app.gradeCallback());
            
            app.StatusLabel = uilabel(app.DashboardPanel, ...
                'Text', 'Ready for submission.', ...
                'Position', [20 130 250 40], ...
                'FontSize', 14, 'FontColor', [1 1 1], ...
                'HorizontalAlignment', 'left');
            
            % Playback / Trajectory Axes on the right side
            app.FeedbackAxes = uiaxes(app.DashboardPanel, ...
                'Position', [320 180 450 300], ...
                'BackgroundColor', [0.12 0.16 0.23], ...
                'XColor', [0.97 0.98 0.99], 'YColor', [0.97 0.98 0.99]);
            title(app.FeedbackAxes, 'Virtual Path Playback', 'Color', [0.97 0.98 0.99]);
            xlabel(app.FeedbackAxes, 'X Position (meters)');
            ylabel(app.FeedbackAxes, 'Y Position (meters)');
            
            app.ScoreGrid = uilabel(app.DashboardPanel, ...
                'Text', '', ...
                'Position', [320 110 450 60], ...
                'FontSize', 16, 'FontColor', [0.06 0.73 0.51], ...
                'FontWeight', 'bold', 'HorizontalAlignment', 'center');
            
            app.ReportLabel = uilabel(app.DashboardPanel, ...
                'Text', '', ...
                'Position', [320 60 450 22], ...
                'FontSize', 12, 'FontColor', [0.8 0.82 0.85], ...
                'HorizontalAlignment', 'center');
                
            app.ReportLinkLabel = uilabel(app.DashboardPanel, ...
                'Text', '', ...
                'Position', [320 30 450 22], ...
                'FontSize', 12, 'FontColor', [0.01 0.52 0.78], ...
                'HorizontalAlignment', 'center');
            
            app.PlagiarismFlagLabel = uilabel(app.DashboardPanel, ...
                'Text', '', ...
                'Position', [20 15 280 22], ...
                'FontSize', 12, 'FontColor', [0.94 0.27 0.27], ...
                'FontWeight', 'bold');
        end
        
        function loginCallback(app)
            stId = strtrim(app.StudentIDEditField.Value);
            if isempty(stId) || length(stId) < 5
                uialert(app.UIFigure, 'Please enter a valid Student Number.', 'Login Error');
                return;
            end
            
            app.StudentID = upper(stId);
            app.WelcomeLabel.Text = ['Logged in as: ', app.StudentID];
            
            % Switch Panels
            app.LoginPanel.Visible = 'off';
            app.DashboardPanel.Visible = 'on';
        end
        
        function trackChangedCallback(app)
            app.SelectedTrack = app.TrackDropDown.Value;
            app.UploadedFilePath = '';
            app.FileStatusLabel.Text = 'No file uploaded yet.';
            app.GradeButton.Enable = 'off';
            
            if strcmp(app.SelectedTrack, 'Simulink Track')
                app.UploadButton.Text = 'Upload File (.slx)';
            else
                app.UploadButton.Text = 'Upload File (.zip)';
            end
        end
        
        function uploadFileCallback(app)
            if strcmp(app.SelectedTrack, 'Simulink Track')
                filter = {'*.slx', 'Simulink Models (*.slx)'};
            else
                filter = {'*.zip', 'Zipped Archives (*.zip)'};
            end
            
            [file, path] = uigetfile(filter, 'Select Submission File');
            if isequal(file, 0) || isequal(path, 0)
                return;
            end
            
            app.UploadedFilePath = fullfile(path, file);
            app.FileStatusLabel.Text = ['Selected: ', file];
            app.GradeButton.Enable = 'on';
        end
        
        function gradeCallback(app)
            if isempty(app.UploadedFilePath) || ~exist(app.UploadedFilePath, 'file')
                uialert(app.UIFigure, 'Submission file not found. Please upload again.', 'Error');
                return;
            end
            
            % Reset UI displays
            app.StatusLabel.Text = 'Starting grading process...';
            app.ScoreGrid.Text = '';
            app.ReportLabel.Text = '';
            app.ReportLinkLabel.Text = '';
            app.PlagiarismFlagLabel.Text = '';
            cla(app.FeedbackAxes);
            drawnow;
            
            % 1. Uniqueness check (SHA-256 and Model Checksum)
            app.StatusLabel.Text = 'Verifying submission uniqueness...';
            drawnow;
            
            fileHash = app.calculateFileHash(app.UploadedFilePath);
            modelChecksum = '';
            isPlagiarism = false;
            
            if strcmp(app.SelectedTrack, 'Simulink Track')
                modelChecksum = app.getSimulinkChecksum(app.UploadedFilePath);
            end
            
            % Query submissions DB
            fields = fieldnames(app.SubmissionsDb);
            for idx = 1:length(fields)
                student = fields{idx};
                history = app.SubmissionsDb.(student);
                if isstruct(history)
                    % Check file hash match
                    if isfield(history, 'fileHash') && strcmp(history.fileHash, fileHash)
                        if ~strcmp(student, app.StudentID)
                            isPlagiarism = true;
                        end
                    end
                    % Check model layout checksum match
                    if ~isempty(modelChecksum) && isfield(history, 'modelChecksum') && strcmp(history.modelChecksum, modelChecksum)
                        if ~strcmp(student, app.StudentID)
                            isPlagiarism = true;
                        end
                    end
                end
            end
            
            if isPlagiarism
                app.PlagiarismFlagLabel.Text = 'WARNING: structural duplicate flagged!';
                disp(['[Plagiarism Checker] Structural copy flagged for ', app.StudentID]);
            end
            
            % Save/Copy submission file to student partition
            student_folder = fullfile(app.SubmissionsDir, app.StudentID);
            if ~exist(student_folder, 'dir')
                mkdir(student_folder);
            end
            
            [~, fname, fext] = fileparts(app.UploadedFilePath);
            % Rename student model to a unique name to prevent shadowing and collision
            if strcmp(app.SelectedTrack, 'Simulink Track')
                savedName = [fname, '_', app.StudentID];
            else
                savedName = fname;
            end
            savedPath = fullfile(student_folder, [savedName, fext]);
            copyfile(app.UploadedFilePath, savedPath);
            
            % 2. Port Validation (Failsafe plumbing check)
            if strcmp(app.SelectedTrack, 'Simulink Track')
                app.StatusLabel.Text = 'Validating model port configuration...';
                drawnow;
                
                [valid, errorMsg] = app.verifyAndSortPorts(savedPath);
                if ~valid
                    app.StatusLabel.Text = 'Grading failed: port check failed.';
                    app.ScoreGrid.Text = 'SCORE: 0% (Port Error)';
                    app.ScoreGrid.FontColor = [0.94 0.27 0.27];
                    
                    % Sync to submissions JSON database
                    app.SubmissionsDb.(app.StudentID) = struct(...
                        'timestamp', char(datetime('now')), ...
                        'score', 0.0, ...
                        'fileHash', fileHash, ...
                        'modelChecksum', modelChecksum, ...
                        'status', 'Port Error', ...
                        'isPlagiarism', isPlagiarism ...
                        );
                    app.saveDb();
                    
                    % Sync to D2L CSV gradebook
                    app.syncToD2L(app.StudentID, 0.0);
                    
                    % Write HTML feedback report with informative error
                    app.generateHtmlReport(0, [], 'Port Error', errorMsg, fileHash, modelChecksum);
                    return;
                end
            end
            
            % 3. Run Simulation
            app.StatusLabel.Text = 'Running lock-step simulation...';
            drawnow;
            
            try
                if strcmp(app.SelectedTrack, 'Simulink Track')
                    % Run Simulink simulation directly
                    [score, trajectory, runStatus, errorMsg] = app.gradeSimulink(savedPath);
                else
                    % Run Python simulator integration
                    [score, trajectory, runStatus, errorMsg] = app.gradePython(savedPath);
                end
            catch ME
                score = 0;
                trajectory = [];
                runStatus = 'Error';
                errorMsg = ME.message;
            end
            
            % 4. Handle grading results
            if strcmp(runStatus, 'Completed')
                app.StatusLabel.Text = 'Grading finished successfully!';
                app.ScoreGrid.Text = sprintf('FINAL SCORE: %.1f%%', score);
                app.ScoreGrid.FontColor = [0.06 0.73 0.51];
            elseif strcmp(runStatus, 'Crashed')
                app.StatusLabel.Text = 'Grading finished: mouse crashed.';
                app.ScoreGrid.Text = sprintf('FINAL SCORE: %.1f%% (Crashed)', score);
                app.ScoreGrid.FontColor = [0.94 0.27 0.27];
            else
                app.StatusLabel.Text = 'Grading finished with errors.';
                app.ScoreGrid.Text = 'SCORE: 0% (Execution Error)';
                app.ScoreGrid.FontColor = [0.94 0.27 0.27];
            end
            
            % Sync to submissions JSON database
            app.SubmissionsDb.(app.StudentID) = struct(...
                'timestamp', char(datetime('now')), ...
                'score', score, ...
                'fileHash', fileHash, ...
                'modelChecksum', modelChecksum, ...
                'status', runStatus, ...
                'isPlagiarism', isPlagiarism ...
                );
            app.saveDb();
            
            % Sync to D2L CSV gradebook
            app.syncToD2L(app.StudentID, score);
            
            % Generate HTML feedback report
            reportUrl = app.generateHtmlReport(score, trajectory, runStatus, errorMsg, fileHash, modelChecksum);
            app.ReportLabel.Text = 'Secure Gradescope report generated. Copy URL:';
            app.ReportLinkLabel.Text = reportUrl;
            
            % 5. Playback Trajectory on UIAxes
            if ~isempty(trajectory)
                app.playbackTrajectory(trajectory);
            end
        end
        
        function hash = calculateFileHash(~, filePath)
            md = java.security.MessageDigest.getInstance('SHA-256');
            fid = fopen(filePath, 'r');
            if fid == -1
                error('Could not open file to calculate hash.');
            end
            data = fread(fid, '*uint8');
            fclose(fid);
            md.update(data);
            digestBytes = int8(md.digest());
            digest = typecast(digestBytes, 'uint8');
            hash = sprintf('%02x', digest);
        end
        
        function checksumStr = getSimulinkChecksum(~, filePath)
            [~, modelName, ~] = fileparts(filePath);
            load_system(filePath);
            try
                cs = Simulink.BlockDiagram.getChecksum(modelName);
                checksumStr = sprintf('%d-%d-%d-%d', cs.Value(1), cs.Value(2), cs.Value(3), cs.Value(4));
            catch
                checksumStr = '';
            end
            close_system(modelName, 0);
        end
        
        function [valid, errorMsg] = verifyAndSortPorts(~, filePath)
            [~, modelName, ~] = fileparts(filePath);
            if bdIsLoaded(modelName)
                close_system(modelName, 0);
            end
            load_system(filePath);
            try
                expected_inports = {'SW1', 'SW2', 'IMU_ACCEL_XYZ', 'IMU_GYRO_XYZ', 'IMU_TEMP', ...
                                    'TOF_LEFT', 'TOF_FRONT', 'TOF_RIGHT', 'V_BATT', ...
                                    'V_LINE_DOWNs', 'V_MOT_ENCODERSs', 'PWR_METER'};
                
                % Check inports existence
                for idx = 1:length(expected_inports)
                    blk = [modelName '/' expected_inports{idx}];
                    if getSimulinkBlockHandle(blk) == -1
                        valid = false;
                        errorMsg = sprintf('Missing expected Input port: "%s"', expected_inports{idx});
                        close_system(modelName, 0);
                        return;
                    end
                end
                
                % Check outports existence (essential ones)
                essential_outports = {'STATE', 'LED0', 'LED1', 'LED2', 'MOTOR_LS', 'MOTOR_RS', ...
                                      'OLED_HEADER', 'OLED_LINE1', 'OLED_LINE2', 'OLED_LINE3', 'OLED_LINE4'};
                for idx = 1:length(essential_outports)
                    blk = [modelName '/' essential_outports{idx}];
                    if getSimulinkBlockHandle(blk) == -1
                        valid = false;
                        errorMsg = sprintf('Missing expected Output port: "%s"', essential_outports{idx});
                        close_system(modelName, 0);
                        return;
                    end
                end
                
                % Force re-indexing of port ordering (always 1 to 12)
                for idx = 1:length(expected_inports)
                    blk = [modelName '/' expected_inports{idx}];
                    set_param(blk, 'Port', num2str(idx));
                end
                
                % Re-index Outports dynamically depending on whether STUDENT_NUMBER and EXPECTED_MINUTES exist
                has_student_metadata = (getSimulinkBlockHandle([modelName '/STUDENT_NUMBER']) ~= -1) && ...
                                       (getSimulinkBlockHandle([modelName '/EXPECTED_MINUTES']) ~= -1);
                
                if has_student_metadata
                    set_param([modelName '/STUDENT_NUMBER'], 'Port', '1');
                    set_param([modelName '/EXPECTED_MINUTES'], 'Port', '2');
                    offset = 2;
                else
                    offset = 0;
                end
                
                for idx = 1:length(essential_outports)
                    blk = [modelName '/' essential_outports{idx}];
                    set_param(blk, 'Port', num2str(idx + offset));
                end
                
                save_system(modelName);
                valid = true;
                errorMsg = '';
            catch ME
                valid = false;
                errorMsg = sprintf('Port validation failed: %s', ME.message);
            end
            close_system(modelName, 0);
        end
        
        function [score, trajectory, runStatus, errorMsg] = gradeSimulink(~, filePath)
            % Setup model workspace paths
            [~, stName, ~] = fileparts(filePath);
            
            % Use mm_sim as the co-simulation harness
            physics_model = 'mm_sim';
            if bdIsLoaded(physics_model)
                close_system(physics_model, 0);
            end
            if bdIsLoaded(stName)
                close_system(stName, 0);
            end
            
            load_system(physics_model);
            
            % Setup local path
            addpath(fileparts(filePath));
            
            % Set subsystem reference to student model
            set_param([physics_model '/Subsystem Reference'], 'ReferencedSubsystem', stName);
            set_param(physics_model, 'StopTime', '30.0');
            
            trajectory = [];
            score = 0;
            runStatus = 'Completed';
            errorMsg = '';
            
            % Start simulation stepping
            try
                % Start base structures
                evalin('base', 'simstruct_init(0);');
                
                % Run standard simulation (changes are in memory, no save needed)
                simout = sim(physics_model);
                
                % Extract trajectory [Time, X, Y, Theta] matrix
                try
                    trajectory = [simout.trajectory.Time, simout.trajectory.Data];
                catch
                    error('Simulation completed but no trajectory timeseries was logged.');
                end
                
                final_x = trajectory(end, 2);
                y_drift_error = sum(abs(trajectory(:, 3)));
                
                % Failsafe collision check using distance transform
                simstruct = evalin('base', 'simstruct');
                map_res = simstruct.mapres;
                map_dt = simstruct.mapdt;
                robot_rad = simstruct.robot_rad;
                
                crashed = false;
                for pt_idx = 1:size(trajectory, 1)
                    tx = trajectory(pt_idx, 2);
                    ty = trajectory(pt_idx, 3);
                    
                    % Convert world coordinates (meters) to pixel indices
                    grid_x = round(tx * map_res) + 1;
                    grid_y = size(map_dt, 1) - round(ty * map_res);
                    
                    % Check bounds
                    if grid_x >= 1 && grid_x <= size(map_dt, 2) && grid_y >= 1 && grid_y <= size(map_dt, 1)
                        dist_to_wall = map_dt(grid_y, grid_x);
                        if dist_to_wall < robot_rad
                            crashed = true;
                            break;
                        end
                    else
                        % Out of bounds of the maze is considered a crash
                        crashed = true;
                        break;
                    end
                end
                
                if crashed
                    runStatus = 'Crashed';
                    score = 0.0;
                else
                    if final_x > 2.0 && y_drift_error < 5.0
                        score = 100.0;
                    else
                        score = max(0.0, 100.0 - y_drift_error * 10.0);
                    end
                end
            catch ME
                runStatus = 'Error';
                errorMsg = ME.message;
            end
            
            close_system(physics_model, 0);
            if bdIsLoaded(stName)
                close_system(stName, 0);
            end
        end
        
        function [score, trajectory, runStatus, errorMsg] = gradePython(app, zipPath)
            errorMsg = '';
            % Unzip student submission to a temporary grading workspace
            student_dir = fileparts(zipPath);
            extract_dir = fullfile(student_dir, 'extracted');
            if exist(extract_dir, 'dir')
                rmdir(extract_dir, 's');
            end
            mkdir(extract_dir);
            unzip(zipPath, extract_dir);
            
            % Find main.py
            main_path = fullfile(extract_dir, 'main.py');
            if ~exist(main_path, 'file')
                score = 0;
                trajectory = [];
                runStatus = 'Error';
                errorMsg = 'Missing main.py in zip archive.';
                return;
            end
            
            % Add path to let python import uct_mouse mock library
            autograder_dir = fileparts(mfilename('fullpath'));
            repo_root = fileparts(fileparts(autograder_dir));
            python_lib_path = fullfile(repo_root, 'python');
            
            % Set environment variable PYTHONPATH so the script loads uct_mouse
            setenv('PYTHONPATH', [python_lib_path, pathsep, extract_dir]);
            
            % Start standard simulation thread in MATLAB
            physics_model = 'mm_betterrobot';
            
            % Spawn run_tcp_autograder asynchronously using a MATLAB background task/timer
            % or run it by spawning the python process in parallel.
            % Since run_tcp_autograder blocks and waits on port 8000, we can spawn Python asynchronously
            % and then run the MATLAB TCP server.
            
            log_path = fullfile(extract_dir, 'student_output.log');
            if ispc
                python_cmd = sprintf('start /B python "%s" > "%s" 2>&1', main_path, log_path);
            else
                python_cmd = sprintf('python "%s" > "%s" 2>&1 &', main_path, log_path);
            end
            
            system(python_cmd); % Start student script in background
            
            % Run autograder server synchronously (blocks until Python script finishes or time limit is hit)
            try
                evalin('base', 'simstruct_init(0);');
                [trajectory, runStatus] = run_tcp_autograder(physics_model, 30.0);
                
                if ~isempty(trajectory)
                    final_x = trajectory(end, 2);
                    y_drift_error = sum(abs(trajectory(:, 3)));
                    if strcmp(runStatus, 'Crashed')
                        score = 0.0;
                    elseif final_x > 2.0 && y_drift_error < 5.0
                        score = 100.0;
                    else
                        score = max(0.0, 100.0 - y_drift_error * 10.0);
                    end
                else
                    score = 0;
                    errorMsg = 'No simulation trajectory logged.';
                end
            catch ME
                score = 0;
                runStatus = 'Error';
                errorMsg = ME.message;
                
                % Append python traceback if log file exists
                if exist(log_path, 'file')
                    fid = fopen(log_path, 'r');
                    if fid > 0
                        log_content = fread(fid, '*char')';
                        fclose(fid);
                        if ~isempty(log_content)
                            errorMsg = sprintf('%s\n\n--- Python Output/Traceback ---\n%s', errorMsg, log_content);
                        end
                    end
                end
            end
        end
        
        function syncToD2L(app, studentId, score)
            % Check if file exists, if not write headers
            if ~exist(app.GradesCsvPath, 'file')
                fid = fopen(app.GradesCsvPath, 'w');
                fprintf(fid, 'OrgDefinedId, Milestone 2 Points Grade, End-of-Line Indicator\n');
                fclose(fid);
            end
            
            % Read existing records
            fid = fopen(app.GradesCsvPath, 'r');
            lines = {};
            while ~feof(fid)
                lines{end+1} = fgetl(fid); %#ok<AGROW>
            end
            fclose(fid);
            
            % Check if student record exists, update if found, append if not
            found = false;
            for idx = 2:length(lines)
                tokens = strsplit(lines{idx}, ',');
                if ~isempty(tokens) && strcmp(strtrim(tokens{1}), studentId)
                    lines{idx} = sprintf('%s, %.1f, #', studentId, score);
                    found = true;
                    break;
                end
            end
            
            if ~found
                lines{end+1} = sprintf('%s, %.1f, #', studentId, score); %#ok<AGROW>
            end
            
            % Rewrite file
            fid = fopen(app.GradesCsvPath, 'w');
            for idx = 1:length(lines)
                if ischar(lines{idx})
                    fprintf(fid, '%s\n', lines{idx});
                end
            end
            fclose(fid);
        end
        
        function reportUrl = generateHtmlReport(app, score, trajectory, status, errorMsg, fileHash, modelChecksum)
            % Create web output directories
            autograder_dir = fileparts(mfilename('fullpath'));
            web_dir = fullfile(autograder_dir, 'web', 'results');
            if ~exist(web_dir, 'dir')
                mkdir(web_dir);
            end
            
            % Generate secure hash path using random UUID
            temp_uuid = char(java.util.UUID.randomUUID().toString());
            md = java.security.MessageDigest.getInstance('SHA-256');
            md.update(uint8(temp_uuid));
            digestBytes = int8(md.digest());
            digest = typecast(digestBytes, 'uint8');
            secureHash = sprintf('%02x', digest);
            reportFileName = [secureHash, '.html'];
            reportPath = fullfile(web_dir, reportFileName);
            
            % Format trajectory points as SVG polyline points
            svgPolyline = '';
            if ~isempty(trajectory)
                % Map coordinates to SVG box (X/Y scaled)
                % trajectory is [Time, X, Y, Theta]
                minX = min(trajectory(:, 2)); maxX = max(trajectory(:, 2));
                minY = min(trajectory(:, 3)); maxY = max(trajectory(:, 3));
                
                spanX = max(0.1, maxX - minX);
                spanY = max(0.1, maxY - minY);
                
                for idx = 1:size(trajectory, 1)
                    % Map coordinates to 400x300 canvas
                    x_svg = 50 + (trajectory(idx, 2) - minX) / spanX * 300;
                    y_svg = 250 - (trajectory(idx, 3) - minY) / spanY * 200;
                    svgPolyline = [svgPolyline, sprintf('%.1f,%.1f ', x_svg, y_svg)]; %#ok<AGROW>
                end
            end
            
            % Build HTML Content
            fid = fopen(reportPath, 'w');
            fprintf(fid, '<!DOCTYPE html>\n<html>\n<head>\n');
            fprintf(fid, '<title>Gradescope Autograder Validation Report</title>\n');
            fprintf(fid, '<style>\n');
            fprintf(fid, 'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #e2e8f0; margin: 40px; }\n');
            fprintf(fid, '.container { max-width: 700px; margin: auto; background-color: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); border: 1px solid #334155; }\n');
            fprintf(fid, '.header { text-align: center; border-bottom: 2px solid #334155; padding-bottom: 20px; }\n');
            fprintf(fid, '.score { font-size: 48px; font-weight: bold; color: #10b981; margin: 20px 0; }\n');
            fprintf(fid, '.crashed { color: #ef4444; }\n');
            fprintf(fid, '.validation-block { border: 2px solid #0284c7; background-color: #0c4a6e; padding: 20px; border-radius: 8px; margin: 30px 0; }\n');
            fprintf(fid, '.validation-block table { width: 100%%; border-collapse: collapse; }\n');
            fprintf(fid, '.validation-block td { padding: 8px; font-size: 14px; }\n');
            fprintf(fid, '.validation-block td.label { font-weight: bold; color: #38bdf8; width: 150px; }\n');
            fprintf(fid, '.plot-container { text-align: center; margin-top: 30px; padding: 15px; background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; }\n');
            fprintf(fid, '.error-msg { background-color: #7f1d1d; border: 1px solid #b91c1c; padding: 15px; border-radius: 6px; font-family: monospace; color: #fecaca; text-align: left; word-break: break-all; }\n');
            fprintf(fid, '</style>\n</head>\n<body>\n');
            
            fprintf(fid, '<div class="container">\n');
            fprintf(fid, '  <div class="header">\n');
            fprintf(fid, '    <h1 style="margin: 0; color: #38bdf8;">UCT Micromouse Validation Report</h1>\n');
            fprintf(fid, '    <p style="color: #94a3b8; margin: 5px 0 0 0;">Automated Autograder Outcomes</p>\n');
            fprintf(fid, '  </div>\n');
            
            % Validation Block (screenshot targets)
            fprintf(fid, '  <div class="validation-block">\n');
            fprintf(fid, '    <h2 style="color: #38bdf8; margin: 0 0 15px 0; font-size: 18px; text-transform: uppercase; letter-spacing: 0.05em;">Gradescope Verification Block</h2>\n');
            fprintf(fid, '    <table>\n');
            fprintf(fid, '      <tr><td class="label">Student ID:</td><td>%s</td></tr>\n', app.StudentID);
            fprintf(fid, '      <tr><td class="label">Grading Time:</td><td>%s</td></tr>\n', char(datetime('now')));
            fprintf(fid, '      <tr><td class="label">Submission Track:</td><td>%s</td></tr>\n', app.SelectedTrack);
            fprintf(fid, '      <tr><td class="label">Run Status:</td><td style="font-weight: bold;">%s</td></tr>\n', status);
            fprintf(fid, '      <tr><td class="label">Final Score:</td><td style="font-size: 20px; font-weight: bold; color: #34d399;">%.1f%%</td></tr>\n', score);
            fprintf(fid, '      <tr><td class="label">File Hash:</td><td style="font-family: monospace; font-size: 11px;">%s</td></tr>\n', fileHash);
            if ~isempty(modelChecksum)
                fprintf(fid, '      <tr><td class="label">Model Checksum:</td><td style="font-family: monospace; font-size: 11px;">%s</td></tr>\n', modelChecksum);
            end
            fprintf(fid, '      <tr><td class="label">Verification Hash:</td><td style="font-family: monospace; font-size: 11px; color: #a5f3fc; font-weight: bold;">%s</td></tr>\n', secureHash);
            fprintf(fid, '    </table>\n');
            fprintf(fid, '  </div>\n');
            
            % Detailed Results
            if strcmp(status, 'Port Error') || strcmp(status, 'Error')
                fprintf(fid, '  <h3 style="color: #ef4444;">Simulation Execution Error</h3>\n');
                fprintf(fid, '  <div class="error-msg">%s</div>\n', errorMsg);
            else
                fprintf(fid, '  <div style="text-align: center;">\n');
                if strcmp(status, 'Crashed')
                    fprintf(fid, '    <div class="score crashed">SCORE: %.1f%%</div>\n', score);
                    fprintf(fid, '    <p style="color: #ef4444; font-weight: bold;">CRASH: Mouse collided with the virtual maze walls.</p>\n');
                else
                    fprintf(fid, '    <div class="score">SCORE: %.1f%%</div>\n', score);
                    fprintf(fid, '    <p style="color: #34d399; font-weight: bold;">SUCCESS: Completed run successfully.</p>\n');
                end
                fprintf(fid, '  </div>\n');
                
                % SVG Trajectory Plot
                if ~isempty(svgPolyline)
                    fprintf(fid, '  <div class="plot-container">\n');
                    fprintf(fid, '    <h3 style="color: #38bdf8; margin: 0 0 15px 0;">Logged Navigation Path</h3>\n');
                    fprintf(fid, '    <svg width="400" height="300" style="background-color: #0f172a; border-radius: 4px;">\n');
                    % Draw grid lines
                    for x_g = 50:50:350
                        fprintf(fid, '      <line x1="%d" y1="50" x2="%d" y2="250" stroke="#334155" stroke-dasharray="2,2"/>\n', x_g, x_g);
                    end
                    for y_g = 50:50:250
                        fprintf(fid, '      <line x1="50" y1="%d" x2="350" y2="%d" stroke="#334155" stroke-dasharray="2,2"/>\n', y_g, y_g);
                    end
                    % Draw path
                    fprintf(fid, '      <polyline points="%s" fill="none" stroke="#38bdf8" stroke-width="3"/>\n', svgPolyline);
                    % Draw start & end marker
                    tokens = strsplit(strtrim(svgPolyline), ' ');
                    if length(tokens) >= 1
                        start_pt = strsplit(tokens{1}, ',');
                        end_pt = strsplit(tokens{end}, ',');
                        fprintf(fid, '      <circle cx="%s" cy="%s" r="6" fill="#10b981" />\n', start_pt{1}, start_pt{2}); % Start
                        fprintf(fid, '      <circle cx="%s" cy="%s" r="6" fill="#ef4444" />\n', end_pt{1}, end_pt{2}); % End/Crash
                    end
                    fprintf(fid, '    </svg>\n');
                    fprintf(fid, '  </div>\n');
                end
            end
            
            fprintf(fid, '</div>\n');
            fprintf(fid, '</body>\n</html>\n');
            fclose(fid);
            
            % Return relative HTTP link format
            reportUrl = ['http://localhost:8000/results/', reportFileName];
        end
        
        function playbackTrajectory(app, trajectory)
            % trajectory is [Time, X, Y, Theta]
            % Setup axis limits
            x_data = trajectory(:, 2);
            y_data = trajectory(:, 3);
            
            minX = min(x_data) - 0.2; maxX = max(x_data) + 0.2;
            minY = min(y_data) - 0.2; maxY = max(y_data) + 0.2;
            
            app.FeedbackAxes.XLim = [minX, maxX];
            app.FeedbackAxes.YLim = [minY, maxY];
            
            % Draw static grid
            grid(app.FeedbackAxes, 'on');
            app.FeedbackAxes.GridColor = [0.2 0.25 0.33];
            
            % Plot the full trail in faint blue
            plot(app.FeedbackAxes, x_data, y_data, 'Color', [0.01 0.52 0.78], ...
                'LineWidth', 1.5, 'LineStyle', ':');
            hold(app.FeedbackAxes, 'on');
            
            % Plot moving mouse marker
            mouseMarker = plot(app.FeedbackAxes, x_data(1), y_data(1), 'o', ...
                'MarkerFaceColor', [0.06 0.73 0.51], 'MarkerEdgeColor', [1 1 1], ...
                'MarkerSize', 10);
            
            % Animation loop
            numPoints = length(x_data);
            step = max(1, round(numPoints / 100)); % Limit to ~100 frames for speed
            
            for idx = 1:step:numPoints
                if ~ishandle(app.UIFigure)
                    return; % app closed
                end
                mouseMarker.XData = x_data(idx);
                mouseMarker.YData = y_data(idx);
                drawnow;
                pause(0.01);
            end
            
            % Put marker at final location
            mouseMarker.XData = x_data(end);
            mouseMarker.YData = y_data(end);
            hold(app.FeedbackAxes, 'off');
        end
    end
end
