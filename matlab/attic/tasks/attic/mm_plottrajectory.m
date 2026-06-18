function mm_plottrajectory(traj,fname,capt,simstruct,bdim)

if nargin<5
  bdim = [];
end

% Raw trajectory data
ts = traj.Time;
tpose = traj.Data;

% Truncate if no movement
li = max(find(sum(abs(diff(tpose)),2)>1e-6));
if isempty(li), li = size(tpose,1); end
ts = ts(1:li);
tpose = tpose(1:li,:);

% Interpolated trajectory for frame rate
fps = 5;
tsi = 0:(1/fps):max(ts);
tposei = interp1(ts,tpose,tsi);

% Block index vector for interpolated points on trajectory
if ~isempty(bdim)
  bvisv = zeros(bdim(1)*bdim(2));
  biv = 6*floor(tposei(:,2)/bdim(3)) + floor(tposei(:,1)/bdim(3)) + 1;
end

% Open figure
fh = figure;
ax = axes('parent',fh);
map = binaryOccupancyMap(simstruct.mapim,simstruct.mapres);
show(map,'Parent',ax); 
set(fh, 'Position', [0, 480, 640, 480]);

% Get robot image info
robot_img = simstruct.robot_img;
robot_imgalpha = simstruct.robot_imgalpha;
robot_imgxyd = simstruct.robot_imgxyd;

% Display robot
x0 = 0.1;  y0 = 0.1;  theta0 = 0;
robot_imgr = imrotate(robot_img,-theta0*180/pi,'crop');
robot_imgalphar = imrotate(robot_imgalpha,-theta0*180/pi,'crop');
hold on;
ih = image(x0+robot_imgxyd,y0+robot_imgxyd,robot_imgr);
set(ih,'AlphaData',robot_imgalphar);
hold off;

% Open video file
v = VideoWriter(fname,'MPEG-4');
v.FrameRate = fps;
%v.VideoCompressionMethod = 'H.264';
open(v);

for i=1:length(tsi)
  t = tsi(i);  x = tposei(i,1);  y = tposei(i,2);  theta = tposei(i,3);  
  
  if ~isempty(bdim)
    bi = biv(i);

    if bvisv(bi)==0
      bd = bdim(3);
      biy = bd*floor((bi-1)/6) + bd/2;  % y center
      bix = bd*rem(bi-1,6) + bd/2;  % x center
      ph = patch([bix-bd/2 bix+bd/2 bix+bd/2 bix-bd/2], ...
                 [biy-bd/2 biy-bd/2 biy+bd/2 biy+bd/2],'r');
      set(ph,'FaceAlpha',0.1,'LineStyle','none');
      bvisv(bi) = 1;
    end
  end

  % Display rotated robot image
  robot_imgr = imrotate(robot_img,-theta*180/pi,'crop');
  robot_imgalphar = imrotate(robot_imgalpha,-theta*180/pi,'crop');
  set(ih,'CData',robot_imgr,'AlphaData',robot_imgalphar,'XData',x+robot_imgxyd,'YData',y+robot_imgxyd);
  title([strrep(capt,'_','\_') ':  t=' sprintf('%06.2f', t)]);

  if i>=2
    xp = tposei(i-1,1);  yp = tposei(i-1,2);
    set(0, 'CurrentFigure', fh);
    lh = line([xp x],[yp y]);
    set(lh,'LineWidth',3,'Color','r');
  end

  drawnow;
  %set(fh,'Visible','off');
  F = getframe(fh);
  writeVideo(v,F);
end

close(v);
close(fh);

% Create a VideoReader object for your video file
r = VideoReader(fname); % Replace 'myVideo.mp4' with your video file name

% Display basic information about the video
disp(['Video Duration: ', num2str(r.Duration), ' seconds']);
disp(['Frame Rate: ', num2str(r.FrameRate), ' fps']);
disp(['Video Height: ', num2str(r.Height), ' pixels']);
disp(['Video Width: ', num2str(r.Width), ' pixels']);
disp(['Number of Frames: ', num2str(r.NumFrames)]); % This requires Image Acquisition Toolbox or Vision Toolbox [1]