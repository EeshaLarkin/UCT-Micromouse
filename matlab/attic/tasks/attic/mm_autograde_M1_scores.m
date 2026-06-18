function [scores,sctext] = mm_autograde_M1_scores(traj,fh)

if nargin<2
  fh = [];
end

% Raw trajectory data
ts = traj.Time;
tpose = traj.Data;

% Total least squares fit
x = tpose(:,1);
y = tpose(:,2);
D = [x y];
D_centered = D - mean(D);
[U, S, V] = svd(D_centered,'econ');
v = V(:, end);
d = dot(v,mean(D));
lv = [v' -d];

% Perpendicular distances
A = lv(1);  B = lv(2);  C = lv(3);
pdists = abs(A*x + B*y + C) / sqrt(A^2 + B^2);

% Maximum distance from straight line fit
maxsld = max(abs(pdists));  

% Travel distances
sfdist = sqrt(sum(diff(tpose([1 end],1:2)).^2));  % distance start to end point
pathlen = sum(sqrt(sum(diff(tpose(:,1:2)).^2,2)));  % distance travelled

% Simulation time corresponding to last mouse motion
fi = max(find(sum(abs(diff(tpose)),2)>1e-4));
if isempty(fi), fi = length(ts); end
stime = ts(fi);

% Compile scores
scores = zeros(1,4);
sctext = cell(1,4);
scores(1) = maxsld;
sctext{1} = 'Maximum deviation from straight line fit to path';
scores(2) = abs(sfdist);
sctext{2} = 'Distance travelled point to point (should be 2m)';
scores(3) = abs(sfdist - 2.0);
sctext{3} = 'Distance between start point and desired end point';
scores(4) = abs(pathlen);
sctext{4} = 'Distance (path length) travelled (should be 2m)';
scores(5) = abs(pathlen - 2.0);
sctext{5} = 'Difference between path length and desired travel distance';
scores(6) = stime;
sctext{6} = 'Total time taken to stop (or end simulation)';

% Display for debug
if fh
  %sh = scatter(x,y,'r.');
  lhv = drawlines2d(lv);
end

