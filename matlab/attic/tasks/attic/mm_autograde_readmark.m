function mark = mm_autograde_readmark(fname,stnum,itemno)

% Load table
T = readtable(fname);
if itemno<1 || itemno>=size(T,2)
  error('Index out of bounds');
end

% Extract the current mark for the specified student and item
mark = NaN;
ri = find(strcmp(T.Stnum,stnum));
if ri
  mark = T{ri,itemno+1};
end

