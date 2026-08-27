function flash_micromouse(buildInfo)
    disp('=== UCT Micromouse Post-CodeGen Flash Hook ===');
    
    % Get repo root directory (two folders up from matlab/simulink)
    script_path = mfilename('fullpath');
    [simulink_dir, ~, ~] = fileparts(script_path);
    [matlab_dir, ~, ~] = fileparts(simulink_dir);
    [repo_root, ~, ~] = fileparts(matlab_dir);
    
    % Change directory to repo root to execute commands
    original_dir = pwd;
    cd(repo_root);
    
    try
        % Prepend standard Homebrew, MacPorts and local paths to PATH environment variable
        % (needed because MATLAB launched from Finder/Dock does not inherit terminal profile PATH)
        sys_path = getenv('PATH');
        setenv('PATH', ['/opt/homebrew/bin:/usr/local/bin:/opt/local/bin:' sys_path]);
        
        disp('Compiling firmware target with CMake...');
        [status, cmdout] = system('cmake --build firmware/build --target simulink_firmware');
        disp(cmdout);
        if status ~= 0
            error('Firmware compilation failed.');
        end
        
        disp('Flashing firmware to STM32 board via st-flash...');
        % Try to locate st-flash on standard paths
        st_flash = 'st-flash';
        if exist('/opt/local/bin/st-flash', 'file')
            st_flash = '/opt/local/bin/st-flash';
        elseif exist('/usr/local/bin/st-flash', 'file')
            st_flash = '/usr/local/bin/st-flash';
        end
        
        [status, cmdout] = system([st_flash ' --reset write firmware/binaries/simulink.bin 0x08000000']);
        disp(cmdout);
        if status ~= 0
            error('Flashing failed. Ensure the STM32 board is connected.');
        end
        disp('Success! Simulink firmware deployed to hardware.');
    catch ME
        cd(original_dir);
        rethrow(ME);
    end
    
    cd(original_dir);
end
