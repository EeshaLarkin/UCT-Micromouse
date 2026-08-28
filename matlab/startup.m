function startup()
    % STARTUP Configures the MATLAB path and build settings for the UCT-Micromouse project
    
    disp('Initializing UCT-Micromouse MATLAB/Simulink environment...');
    
    % Find the absolute parent repository root based on this script's location
    mfilePath = mfilename('fullpath');
    matlabDir = fileparts(mfilePath);
    projectRoot = fileparts(matlabDir);
    
    % Add essential directories to the MATLAB path
    addpath(fullfile(projectRoot, 'matlab', 'simulink'));
    addpath(fullfile(projectRoot, 'matlab', 'simulator'));
    
    % Configure Simulink cache and code generation directories to redirect build files
    % to the central build/ directory to keep the root directory clean
    try
        Simulink.fileGenControl('set', ...
            'CacheFolder', fullfile(projectRoot, 'build', 'slprj'), ...
            'CodeGenFolder', fullfile(projectRoot, 'build'), ...
            'createDir', true);
        disp('Simulink cache and code-generation folders redirected to build/.');
    catch
        warning('Could not configure Simulink build folders. Ensure Simulink is installed.');
    end
    
    % If running on Windows, configure models to link Winsock2 (ws2_32.lib)
    % to prevent simulation target link errors (unresolved __imp_socket, etc.)
    if ispc
        disp('Windows detected. Ensuring Winsock2 (ws2_32.lib) is configured in project models...');
        models = {'StudentTemplate', 'StudentTemplate_matlabfunc', 'UCT_KDeploy', 'milestone1_square', 'milestone2_maze'};
        for i = 1:length(models)
            model = models{i};
            try
                if exist(which([model '.slx']), 'file')
                    load_system(model);
                    libs = get_param(model, 'SimUserLibraries');
                    if isempty(libs) || ~contains(libs, 'ws2_32')
                        set_param(model, 'SimUserLibraries', 'ws2_32.lib');
                        save_system(model);
                        fprintf('  Configured %s.slx SimUserLibraries -> ws2_32.lib\n', model);
                    end
                end
            catch ME
                warning('Failed to configure library link settings for %s: %s', model, ME.message);
            end
        end
    end
    
    disp('MATLAB path configured successfully.');
    disp('Ready for local TCP/IP Co-Simulation on localhost:8000.');
end
