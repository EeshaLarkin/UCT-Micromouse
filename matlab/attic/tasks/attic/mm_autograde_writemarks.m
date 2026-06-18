function mm_autograde_writemarks(fname,stnum,items,marks)

% Create file if not exists
if ~(exist(fname,'file')==2)
  ncv = 30;
  vt = {'string'};
  vn = {'Stnum'};
  for i=1:ncv
    vt{end+1} = 'double'; 
    vn{end+1} = ['T' num2str(i)];
  end
  T = table('Size',[0 ncv+1],'VariableTypes',vt,'VariableNames',vn);
  writetable(T,fname);
end

% Load table
T = readtable(fname);

% Find row (add if necessary)
ri = strcmp(T.Stnum,stnum);
if ~any(ri)
  nr = {stnum};
  for i=1:size(T,2)-1
    nr{end+1} = NaN;
  end
  T = [T; cell2table(nr,'VariableNames',T.Properties.VariableNames)];
  ri = size(T,1);
end

% Modify row
T{ri, items+1} = marks;

% Write the updated table back to the file
writetable(T, fname);



