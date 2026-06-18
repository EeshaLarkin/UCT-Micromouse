function fh = plotrobot(x,y,theta,simstruct,fh)

if nargin<5 || isempty(fh)
  fh = figure;
  ax = axes('parent',fh);

  % Display map
  if isfield(simstruct,'mapim') && isfield(simstruct,'mapres')
    map = binaryOccupancyMap(simstruct.mapim,simstruct.mapres);
    show(map,'Parent',ax); 
  else
    axis([-2 2 -2 2]);
  end

  % Display robot
  if isfield(simstruct,'robot_img') && isfield(simstruct,'robot_imgalpha') && isfield(simstruct,'robot_imgxyd')

    % Get robot
    robot_img = simstruct.robot_img;
    robot_imgalpha = simstruct.robot_imgalpha;
    robot_imgxyd = simstruct.robot_imgxyd;

    % Display robot
    robot_imgr = imrotate(robot_img,-theta*180/pi,'crop');
    robot_imgalphar = imrotate(robot_imgalpha,-theta*180/pi,'crop');
    hold on;
    ih = image(x+robot_imgxyd,y+robot_imgxyd,robot_imgr);
    set(ih,'AlphaData',robot_imgalphar);
    hold off;
  end

  set(fh,'UserData',ih);
end

% Get image handle
ih = get(fh,'UserData');

% Display robot
if isfield(simstruct,'robot_img') && isfield(simstruct,'robot_imgalpha') && isfield(simstruct,'robot_imgxyd')
  robot_img = simstruct.robot_img;
  robot_imgalpha = simstruct.robot_imgalpha;
  robot_imgxyd = simstruct.robot_imgxyd;

  % Display rotated robot image
  robot_imgr = imrotate(robot_img,-theta*180/pi,'crop');
  robot_imgalphar = imrotate(robot_imgalpha,-theta*180/pi,'crop');
  set(ih,'CData',robot_imgr,'AlphaData',robot_imgalphar,'XData',x+robot_imgxyd,'YData',y+robot_imgxyd);
end

drawnow('limitrate', 'nocallbacks');