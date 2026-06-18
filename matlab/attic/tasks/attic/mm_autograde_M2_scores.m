function [scores,sctext] = mm_autograde_M2_scores(simout,bdim)

if nargin<2
  bdim = [4 6 0.2];
end

% Raw trajectory data
ts = simout.trajectory.Time;
tpose = simout.trajectory.Data;

% Block index vector for points on trajectory
bvisv = zeros(bdim(1)*bdim(2));
biv = 6*floor(tpose(:,2)/bdim(3)) + floor(tpose(:,1)/bdim(3)) + 1;

% Proportion of maze explored
[counts,centers] = hist(biv,1:bdim(1)*bdim(2));
pme = sum(counts>1)/(bdim(1)*bdim(2));  % proportion of maze explored

% Distance travelled
pathlen = sum(sqrt(sum(diff(tpose(:,1:2)).^2,2)));  % distance travelled

% Last time step of simulation
lastsimtime = simout.tout(end);

% Simulation time corresponding to last mouse motion
fi = max(find(sum(abs(diff(tpose)),2)>1e-4));
if isempty(fi), fi = length(ts); end
stime = ts(fi);

% Find first time for complete exploration
bc = zeros(bdim(1)*bdim(2),1);
comptime = -1;
for j=1:length(ts)
  bc(biv(j)) = 1;
  if all(bc)
    comptime = ts(j);
    break;
  end
end

% Exit state
exitstate = simout.state.Data(end);

% Crashed?
crashed = simout.crash.Data(end);

% Last block index
lastblock = biv(end);

% Compile scores
scores = zeros(1,1);
sctext = cell(1,1);
scores(1) = pme;
sctext{1} = 'Proportion of maze explored (0-1)';
scores(2) = abs(pathlen);
sctext{2} = 'Total distance travelled (path length)';
scores(3) = comptime;
sctext{3} = 'First time for complete exploration';
scores(4) = lastsimtime;
sctext{4} = 'Last time instant for simulation';
scores(5) = stime;
sctext{5} = 'Last time mouse moved in simulation';
scores(6) = exitstate;
sctext{6} = 'Final state on exit';
scores(7) = crashed;
sctext{7} = 'Exit with crash flag set';
scores(8) = lastblock;
sctext{8} = 'Last block visited (1 for home)';
% scores(6) = stime;
% sctext{6} = 'Total time taken to stop (or end simulation)';