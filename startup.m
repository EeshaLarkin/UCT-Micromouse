function startup()
    % STARTUP Configures the MATLAB path and build settings for the UCT-Micromouse project
    
    disp('Initializing UCT-Micromouse MATLAB/Simulink environment...');
    
    projectRoot = pwd;
    
    % Add essential directories to the MATLAB path
    addpath(fullfile(projectRoot, 'matlab', 'simulink'));
    addpath(fullfile(projectRoot, 'matlab', 'simulator'));
    
    % Configure Simulink cache and code generation directories to redirect build files
    % to the central build/ directory to keep the root directory clean
    if exist('Simulink.fileGenControl', 'class')
        try
            Simulink.fileGenControl('set', ...
                'CacheFolder', fullfile(projectRoot, 'build', 'slprj'), ...
                'CodeGenFolder', fullfile(projectRoot, 'build', 'UCT_KDeploy_ert_rtw'), ...
                'createDir', true);
            disp('Simulink cache and code-generation folders redirected to build/.');
        catch
            warning('Could not configure Simulink build folders. Ensure Simulink is installed.');
        end
    end
    
    disp('MATLAB path configured successfully.');
    disp('Ready for local TCP/IP Co-Simulation on localhost:8000.');
end
