clear all;
simstruct_init(3);

force_refresh = 0;
w = warning('off','all');

% Current unit test simulation file
emethod = 1;
simfilesc = {'mm_autograde_M1a','mm_autograde_M1b'};
simfile = simfilesc{emethod};

% Iterate over all submissions
%rootdir = '/Users/nicolls/Desktop/Milestone 1 file submissions Download 18 September 2025 251 PM';
%rootdir = '/Users/nicolls/Desktop/Milestone 1 StudentTemplate.slx resubmission Download 03 October 2025 841 AM';
%rootdir = '/Users/nicolls/Desktop/Milestone 1 StudentTemplate.slx resubmission Download 07 October 2025 1034 AM';
%rootdir = '/Users/nicolls/proj/eee3097s/2025/Milestone 1 StudentTemplate.slx resubmission 2 Download 19 October 2025 105 PM';
%rootdir = '/Users/nicolls/proj/eee3097s/2025/Milestone 1 StudentTemplate.slx resubmission Download 19 October 2025 107 PM';
%rootdir = '/Users/nicolls/proj/eee3097s/2025/M1_sim/manually_run_leftovers/49784-80500 - DMRNEJ001 - Demirtas, Nejdet - 17 October 2025 319 PM/StudentTemplate_DMRNEJ001_M1';
rootdir = '/Users/nicolls/proj/eee3097s/2025/SNAGS_TO_HANDLE/M1_sim_OS';
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
%fls = fls(1);

nfailed = [];
for i=1:length(fls)
  stnumc = extract(fls(i).folder,lettersPattern(6)+digitsPattern(3));
  stnum = upper(stnumc{1});
  disp(['Student number: ' stnum]);

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
  close_system(sttempl_filename,0);

  close_system(simfile,0);
  [status,msg] = copyfile(['/Users/nicolls/proj/micromouse/Micromouse' filesep simfile '.slx'],'.');
  %load_system(simfile);
  open_system(simfile);

  % Simulate until stoppped or maxstime reached
  stime = 60;
  maxstime = 960;
  failed = 0;
  while stime<=maxstime
    disp(['stime=' num2str(stime)]);
    set_param(simfile,'StopTime',num2str(stime));

    % Run simulation and get trajectory
    try

      % Limit wall clock simulation time if desired
      if 1
        set_param([simfile '/Subsystem Reference'], 'ReferencedSubsystem', sttempl_filename);
        save_system(simfile);
        %simout = sim('mm_autograde_M1','CaptureErrors','on');
        simout = sim(simfile);
      else
        simin = Simulink.SimulationInput(simfile);
        simin = simin.setBlockParameter([simfile '/Subsystem Reference'], 'ReferencedSubsystem', sttempl_filename);
        simin  = setModelParameter(simin,TimeOut=60*5);
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
      failed = 1;
      break;
    end
  
    % Determine whether simulation can stop
    [scores,sctext] = mm_autograde_M1_scores(simout.trajectory);
    if scores(4)==0 || scores(4)>6 || scores(6)<(stime-1)
      break;
    end

    stime = 2*stime;
  end
  if failed, continue; end

  % Populate spreadsheet with scores
  items = (emethod-1)*(length(scores)+1) + (1:length(scores));
  mm_autograde_writemarks('autograde_M1.xls',stnum,items,scores);

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
      mm_plottrajectory(simout.trajectory,fnamev,['Case ' simfile],simstruct);
      success = 1;
    catch
      disp('Error calling mm_plottrajectory');
    end
    if success, break; end
  end
  
end

disp('After run: nfailed=');
disp(nfailed);