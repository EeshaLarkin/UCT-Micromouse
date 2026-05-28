function map = amaze_mm(m,n,branching,detail,shortest)
  % A maze generator for micromouse
  %
  % map = amaze_mm(m,n,branching,detail,shortest)
  %
  % (m,n) = maze is m-by-n.
  % branching = 'first', 'middle', or 'last'.
  %    Experiment with all three.
  % detail = false or true,
  %    Show generation of maze.
  % shortest = false or true.
  %    Show shortest path from upper left to lower right.
  %
  % Defaults:
  % amaze(16,16,'middle',false,true)
  %
  % See also: amazing, graph, graph/shortestpath, delsq, numgrid,
  % https://blogs.mathworks.com/cleve/2019/03/04.
  %
  % Modifications for rectangular grid and micromouse by Fred Nicolls,
  % 2025.
      
  if nargin<1, m = 16; end
  if nargin<2, n = 16; end
  if nargin<3, branching = 'middle'; end
  if nargin<4, detail = false; end
  if nargin<5, shortest = true; end

  if mod(m,2) || mod(n,2), error("Inputs m and n must be even"); end
  
  % Barriers: discrete Laplacian on a square grid
  gpb = reshape(1:(m+1)*(n+1),[m+1 n+1]);  % grid points barriers
  gpbz = zeros(m+3,n+3);  gpbz(2:m+2,2:n+2) = gpb;
  Db = delsq(gpbz);
  B = graph(logical(Db),'omitselfloops');
  
  % Cells: initially just nodes no edges
  gpc = reshape(1:m*n,[m n]);  % grid points cells
  gpcz = zeros(m+2,n+2);  gpcz(2:m+1,2:n+1) = gpc;
  Dc = delsq(gpcz);
  C = graph(logical(Dc),'omitselfloops');
  
  if detail, [Bp,Cp] = plotem(B,C); end

  % Target cells in center
  tcs = gpc(m/2:m/2+1,n/2:n/2+1);

  % Setup
  available = 1:m*n;  % Nodes we haven't visited yet
  branches = [];
  tree = zeros(0,2);  % Depth first search
  p = 1;

  % Break when available is empty
  while 1  
    available(p) = 0;
    if ~any(available), break; end
  
    % As per Micromouse rules 1.3
    if p==1
     ngh = m+1;
    else
     [~,~,ngh] = find(available(neighbors(C,p)));
    end
    
    if ~isempty(ngh) && ~ismember(p,tcs)
      idx = randi(length(ngh));  % Random choice
      q = ngh(idx);              % Next cell
      if length(ngh)>1
        % Could have chosen another neighbor
        branches(end+1) = p;
      end

      % Add a cell and remove a barrier
      tree(end+1,:) = [p q];
      [i,j] = wall(p,q,m);
      B = rmedge(B,i,j);
      
      % Show detail
      if detail                
        highlight(Bp,i,j,'LineStyle','none');
        highlight(Cp,p,q,'EdgeColor',darkgreen,'LineStyle','-');
        drawnow; 
      end

      % Reached target
      if any(ismember(q,tcs))
        available(tcs) = 0;  % all cells in target block 

        % Central target block edges to remove
        [i1,j1] = wall(tcs(1,1),tcs(1,2),m);
        [i2,j2] = wall(tcs(2,1),tcs(2,2),m);
        [i3,j3] = wall(tcs(1,1),tcs(2,1),m);
        [i4,j4] = wall(tcs(1,2),tcs(2,2),m);
       
        % Remove edges
        B = rmedge(B,i1,j1);
        B = rmedge(B,i2,j2);
        B = rmedge(B,i3,j3);
        B = rmedge(B,i4,j4);

        % Add shortest path information
        tree(end+1,:) = [tcs(1,1) tcs(1,2)];
        tree(end+1,:) = [tcs(2,1) tcs(2,2)];
        tree(end+1,:) = [tcs(1,1) tcs(2,1)];
        tree(end+1,:) = [tcs(1,2) tcs(2,2)];
        
        % Update display
        if detail
          highlight(Bp,i1,j1,'LineStyle','none');
          highlight(Bp,i2,j2,'LineStyle','none');
          highlight(Bp,i3,j3,'LineStyle','none');
          highlight(Bp,i4,j4,'LineStyle','none');
          drawnow
        end

        continue;
      end
      
      p = q;
    
    else
    
      for p=branches
        if all(available(neighbors(C,p))==0)
          branches(branches==p) = [];
        end
      end
    
      % Take another branch
      switch branching
        case 'first'
          idx = 1;
        case 'last'
          idx = length(branches);
        otherwise
          idx = round(length(branches)/2);
      end

      p = branches(idx);
      branches(idx) = [];
    end
  end

  C = graph(tree(:,1),tree(:,2));
  if detail
    [~,Cp] = plotem(B,C,'none');
  end

  if shortest && detail
    [path1,len1] = shortestpath(C,1,tcs(1));
    [path2,len2] = shortestpath(C,1,tcs(2));
    [path3,len3] = shortestpath(C,1,tcs(3));
    [path4,len4] = shortestpath(C,1,tcs(4));
    lens = [len1 len2 len3 len4];
    [~,ii] = min(lens);
    [path,len] = shortestpath(C,1,tcs(ii));

    highlight(Cp,path,'edgecolor',darkgreen,'lineStyle','-','nodecolor',darkgreen,'marker','o')
    highlight(Cp,[1 m*n]);
    title(['length = ' int2str(len)]);
  end

  % Generate occupancy map
  bdim = 0.180;  % maze block dimension (meters)
  pydim = 0.02;  % pylon edge dimension (meters)
  wtdim = 0.006;  % wall thickness dimension (meters)
  res = 500;  % resolution (points per meter)
  map = genmap(bdim,pydim,wtdim,res);


  % -------------------------------------------------------------

  function [i,j] = wall(p,q,m)
    % Wall [i,j] blocks path [p,q]
    switch q-p
      case -m  % west
        i = p+ceil(p/m)-1;
        j = i+1;
      case -1  % north
        i = p+ceil(p/m)-1;
        j = i+(m+1);
      case 1  % south
        i = p+ceil(p/m);
        j = i+(m+1);
      case m  % east
        i = p+ceil(p/m)+(m+1)-1;
        j = i+1;
    end
  end
  
  function dg  = darkgreen
    dg = [0 .5 0];
  end

  function [Bp,Cp] = plotem(B,C,Ccolor)
    % Plot both graphs
    if nargin < 3
      Ccolor = darkgreen;
    end
    if strcmp(Ccolor,'none')
      Ccolor = 'white';
      linestyle = 'none';
    else
      linestyle = '-';
    end
    if numedges(B) > 400
      lw = 2;  ms = 2;
    else
      lw = 3;  ms = 4;
    end
  
    xloc = reshape(repmat(0:n,m+1,1),[],1);
    yloc = reshape(repmat(fliplr(0:m)',1,n+1),[],1);
    Bp = plot(B,'XData',xloc, ...
                'YData',yloc, ...
                'linewidth',lw, ...
                'markersize',ms, ...
                'nodelabel',{});  %axis ij;
    axis equal;
    set(gca,'xtick',[],'ytick',[]);
    th = text(xloc,yloc,string(1:length(xloc)));
  
    hold on
    xloc = reshape(repmat(0:n-1,m,1),[],1)'+0.5;
    yloc = reshape(repmat(fliplr(0:m-1)',1,n),[],1)' + 0.5;
    Cp = plot(C,'XData',xloc, ...
                'YData',yloc, ...
                'NodeLabel',{}, ...
                'NodeColor',Ccolor, ...
                'LineStyle',linestyle, ...
                'EdgeColor','white', ...
                'linewidth',3);
    %th = text(xloc,yloc,string(1:length(xloc)));
  
    hold off
    drawnow
  end

  function map = genmap(bdim,pydim,wtdim,res)
    % bdim - block dimension (meters)
    % pydim - pylon dimension (meters)
    % wdim - wall thickness dimension (meters)
    % res - resolution (points per meter)

    pyh = ceil(pydim*res/2);  % pylon half dimension
    wth = ceil(wtdim*res/2);  % wall half thickness
    bdh = ceil(bdim*res/2);  % block half dimension

    % Map and outside edges
    mapim = zeros(ceil(m*bdim*res),ceil(n*bdim*res));

    % Pylons
    %[Xm,Ym] = meshgrid(0:n,0:m);
    [Xm,Ym] = meshgrid(0:n,fliplr(0:m));
    gpbc = cat(3,Xm*2*bdh,Ym*2*bdh)+1;  % grid point barrier centers
    xpc = reshape(gpbc(:,:,1),[],1);  ypc = reshape(gpbc(:,:,2),[],1);
    hs = ceil(0.01*res);
    rparm = [xpc-hs ypc-hs 2*hs*ones(size(xpc)) 2*hs*ones(size(xpc))];
    mapim = insertShape(mapim,'filled-rectangle',rparm,'color','w');

    % Edges
    be = table2array(B.Edges)
    hef = diff(xpc(be),1,2)>0;  % horizontal edges
    rw = 2*wth*ones(size(hef));  rw(hef) = 2*bdh;
    rh = 2*wth*ones(size(hef));  rh(~hef) = 2*bdh;
    xcm = mean(xpc(be),2);  ycm = mean(ypc(be),2);
    rparm = [xcm-rw/2 ycm-rh/2 rw rh];
    mapim = insertShape(mapim,'filled-rectangle',rparm,'color','w');

    % Generat output
    mapim = mapim(:,:,1)>0;
    map = binaryOccupancyMap(mapim,res);
  end

end % amaze