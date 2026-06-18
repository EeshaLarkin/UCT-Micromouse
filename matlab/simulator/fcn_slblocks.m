    function blkStruct = slblocks
    %SLBLOCKS Defines the Simulink Library Browser for a custom library.

    blkStruct.Name = 'UCT FN Devel Library'; % Name displayed in the Library Browser
    blkStruct.OpenFcn = 'devel_lib'; % Name of your .slx library file (without extension)
    blkStruct.MaskDisplay = ''; % Optional: Custom icon for the library in the browser
    blkStruct.Browser = 1; % Indicates this is a top-level library in the browser
