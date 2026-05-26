function startup()
    % STARTUP Configures the MATLAB environment for the UCT-Micromouse project
    % This script runs automatically when the MATLAB project is opened.
    
    disp('Initializing UCT-Micromouse Simulator Environment...');
    
    % Get the root directory of this project (assumes this script is in matlab/scripts)
    projectRoot = fileparts(fileparts(mfilename('fullpath')));
    
    % Add essential directories to the MATLAB path
    addpath(fullfile(projectRoot, 'models'));
    addpath(fullfile(projectRoot, 'scripts'));
    addpath(fullfile(projectRoot, 'data'));
    
    disp('Paths configured successfully.');
    disp('Ready for Local TCP/IP Co-Simulation on port 8000.');
end