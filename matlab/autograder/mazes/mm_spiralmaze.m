function map = testmaze_mm()
 
% Generate occupancy map
m = 4;  n = 6;
bdim = 0.20;  % maze block dimension (meters)
pydim = 0.02;  % pylon edge dimension (meters)
wtdim = 0.006;  % wall thickness dimension (meters)
res = 500;  % resolution (points per meter)
map = genmap(bdim,pydim,wtdim,res);


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
  %be = table2array(B.Edges);
  be = [1 2; 2 3; 3 4; 4 5; 5 10; 10 15; 15 20; 20 25; 25 30; 30 35; ...
        35 34; 34 33; 33 32; 32 31; 1 6; 6 11; 11 16; 16 21; 21 26; 26 31; ...
        2 7; 7 12; 12 17; 17 22; 22 27; 27 28; 28 29; 24 29; 19 24; 14 19; 9 14; ...
        9 8; 8 13; 13 18; 18 23];
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

end