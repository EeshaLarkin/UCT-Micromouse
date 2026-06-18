clear all;
simstruct_init(4);
simstruct.robot_rad = 0.8*simstruct.robot_rad;  % soften collision detection

force_refresh = 0;
w = warning('off','all');

% Current unit test simulation file
emethod = 3;
simfilesc = {'mm_autograde_M2a','mm_autograde_M2b','mm_autograde_M2c'};
simfile = simfilesc{emethod};
switch emethod
  case 1
    simstruct_init(4);
  case 2
    simstruct_init(0);
  case 3
    simstruct_init(0);
end

% Location of micromouse repo
script_dir = fileparts(mfilename('fullpath'));
% Go up 4 levels from matlab/autograder/tasks/milestone2_turns to get repository root
mmrepodir = fileparts(fileparts(fileparts(fileparts(script_dir))));

% Iterate over all submissions
%rootdir = 'C:\Users\user\OneDrive - University of Cape Town\M2_sim\Milestone 2 StudentTemplate.slx submission Download 21 October 2025 950 PM';
%rootdir = '/Users/nicolls/proj/eee3097s/2025/M2_sim/Milestone 2 StudentTemplate.slx submission Download 21 October 2025 950 PM';
rootdir = '/Users/nicolls/proj/eee3097s/2025/M2_sim/Milestone 2 StudentTemplate.slx submission Download 21 October 2025 950 PM';
slxext = '*.slx';
fls = dir(fullfile(rootdir, '**', slxext));
for i=1:length(simfilesc)
  fls = fls(~strcmp({fls(:).name},[simfilesc{i} '.slx']));
end

% Remove duplicate submissions based on date
stnumsdi = zeros(size(fls));  % items to delete
stnumsc = cell(1,length(fls));
for i=1:length(stnumsc)
  stnumc = extract(fls(i).folder,lettersPattern(6)+digitsPattern(3));
  stnumsc{i} = upper(stnumc{1});
end
stnumsr = unique(stnumsc);
while ~isempty(stnumsr)
  stnum = stnumsr{1};
  stnumsr = stnumsr(2:end);

  % Nothing to do
  ii = strmatch(stnum,stnumsc,'exact');
  if length(ii)==1, continue; end

  % Multiple choices
  bj = 1;
  for j=2:length(ii)
    if datetime(fls(ii(j)).date)>datetime(fls(ii(bj)).date)
      bj = j;
    end
  end
  stnumsdi(ii(ii~=ii(bj))) = 1;
end
fls = fls(~stnumsdi);  % delete flagged files

% Restrict for development
%fls = fls(16);

nfailed = [];
for i=1:length(fls)
  stnumc = extract(fls(i).folder,lettersPattern(6)+digitsPattern(3));
  stnum = upper(stnumc{1});
  disp(['Student number: ' stnum]);
  %if strmatch(stnum,'SLTEMI002'), keyboard; end

  % Output filenames
  fnamer = [fls(i).folder filesep simfile '_results.txt'];
  fnamev = [fls(i).folder filesep simfile '_output.mp4'];

  if force_refresh
    delete([fls(i).folder filesep simfile '_error.txt']);
    delete(fnamer);
    delete(fnamev);
    delete([fls(i).folder filesep simfile '.slx']);
  end
  if exist(fnamer,'file')==2 && exist(fnamev,'file')==2
    disp(['Skipping ' stnum ' because output files exist']);
    delete([fls(i).folder filesep simfile '_error.txt']);
    continue; 
  end

  % Load main simulink file and set subsystem reference
  [status,msg] = copyfile([fls(i).folder filesep fls(i).name],'student');
  [~, sttempl_filename, ~] = fileparts(fls(i).name);
  
  % --- ENFORCE PORT WIRING ORDER ---
  % Subsystem references wire by Port Index, not Name! If a student deletes and 
  % re-adds a port, the index changes and cross-wires the physics engine.
  % This forces the ports back into the exact order the autograder expects.
  try
      load_system(sttempl_filename);
      
      % TODO: Adjust these arrays to match the exact names of the ports in your template!
      expected_inports = {'ToF_L', 'ToF_C', 'ToF_R', 'Enc_L', 'Enc_R', 'Gyro', 'Vbatt'}; 
      expected_outports = {'PWM_L', 'PWM_R'}; 
      
      for p = 1:length(expected_inports)
          blk = [sttempl_filename '/' expected_inports{p}];
          if getSimulinkBlockHandle(blk) ~= -1
              set_param(blk, 'Port', num2str(p));
          end
      end
      for p = 1:length(expected_outports)
          blk = [sttempl_filename '/' expected_outports{p}];
          if getSimulinkBlockHandle(blk) ~= -1
              set_param(blk, 'Port', num2str(p));
          end
      end
      save_system(sttempl_filename);
  catch
      disp(['[Warning] Could not auto-sort ports for: ' stnum]);
  end
  % ---------------------------------
  
  close_system(sttempl_filename,0);

  close_system(simfile,0);
  [status,msg] = copyfile([mmrepodir filesep simfile '.slx'],'.');
  %load_system(simfile);
  open_system(simfile);
  
  % Run simulation and get trajectory
  try

    % Limit simulation time
    stime = 60*3;
    if 1
      set_param([simfile '/Subsystem Reference'], 'ReferencedSubsystem', sttempl_filename);
      set_param(simfile,'StopTime',num2str(stime));
      save_system(simfile);
      %simout = sim('mm_autograde_M1','CaptureErrors','on');
      simout = sim(simfile);
    else
      simin = Simulink.SimulationInput(simfile);
      simin = simin.setBlockParameter([simfile '/Subsystem Reference'], 'ReferencedSubsystem', sttempl_filename);
      simin  = setModelParameter(simin,StopTime=num2str(stime));
      save_system(simfile);
      simout = sim(simin);
    end

  catch ME
    disp(['Error for index ' num2str(i)]);
    errmsg = eraseTags(ME.getReport);
  
    % Save errors to student submission folder
    [status,msg] = copyfile([simfile '.slx'],fls(i).folder);
    fid = fopen([fls(i).folder filesep simfile '_error.txt'],'w');
    fprintf(fid, '%s\n',errmsg);  fclose(fid);
    disp(ME.getReport);
    nfailed(end+1) = i;
    continue;  % next submission
  end

  % Get score components from simulation output
  [scores,sctext] = mm_autograde_M2_scores(simout,[4 6 0.2]);

  % Populate spreadsheet with scores
  items = (emethod-1)*(length(scores)+1) + (1:length(scores));
  mm_autograde_writemarks([rootdir filesep 'autograde_M2.xls'],stnum,items,scores);

  % Save output results as text
  fid = fopen(fnamer,'w');
  for j=1:length(scores)
    fprintf(fid, '%s: ', sctext{j});  
    fprintf(fid, '%f\n', scores(j));
  end
  fclose(fid);

  % Save other outputs
  [status,msg] = copyfile([simfile '.slx'],fls(i).folder);

  % Repeated try mm_plottrajectory
  success = 0;
  for j=1:5
    try
      mm_plottrajectory(simout.trajectory,fnamev,['Case ' simfile],simstruct,[4 6 0.2]);
      success = 1;
    catch
      disp('Error calling mm_plottrajectory');
    end
    if success, break; end
  end
  
end

disp('After run: nfailed=');
disp(nfailed);