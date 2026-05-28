%function amaze_mm(n,branching,detail,shortest)
norig = 7;
n = 6;

branching = 'middle';
detail = true;
shortest = true;
    % A maze generator.
    %
    % amaze(n,branching,detail,shortest)
    %
    % n, maze is n-by-n.
    % branching = 'first', 'middle', or 'last'.
    %    Experiment with all three.
    % detail = false or true,
    %    Show generation of maze.
    % shortest = false or true.
    %    Show shortest path from upper left to lower right.
    %
    % Defaults:
    % amaze(15,'middle',false,true)
    %
    % See also: amazing, graph, graph/shortestpath, delsq, numgrid,
    % https://blogs.mathworks.com/cleve/2019/03/04.
    
    % Copyright 2019 Cleve Moler
    % Copyright 2019 The MathWorks, Inc.
        
    % if nargin < 1
    %     n = 15;
    % end
    % if nargin < 2
    %     branching = 'middle';
    % end
    % if nargin < 3
    %     detail = false;
    % end
    % if nargin < 4
    %     shortest = true;
    % end

    % Barriers, initially n^2 barriers.
    % Discrete Laplacian on a square grid.
    Db = delsq(numgrid('S',(n+1)+2));
    B = graph(logical(Db),'omitselfloops');

    m = 5;
    m = n + 1;
    ng = zeros(m+2,n+1+2);
    ng(2:m+1,2:n+1+1) = reshape(1:m*(n+1),[m n+1]);
    Dbn = delsq(ng);
    Bn = graph(logical(Dbn),'omitselfloops');
    %cnn = reshape(ng(m/2+1:m/2+2,n/2+1:n/2+2),[],1);  % central nodes




    % Cells, initially just nodes, no edges.
    nr = n+1-1;  % m^2 cells
    Dc = delsq(numgrid('S',nr+2));
    C = graph(logical(Dc),'omitselfloops');
    
    ngc = zeros(m+1,(n+1)+1);
    ngc(2:m,2:(n+1)) = reshape(1:(m-1)*((n+1)-1),[m-1 (n+1)-1]);
    Dcn = delsq(ngc);
    Cn = graph(logical(Dcn),'omitselfloops');


    
    if detail
       [Bp,Cp] = plotem(B,C,m,(n+1));
       %[Bpn,Cpn] = plotem(Bn,Cn,m,n);
    end


    %return;

    
    available = 1:nr^2; % Nodes we haven't visited yet.
    branches = [];
    tree = zeros(0,2); % Depth first search.
    p = 1;

    while 1  % Break when available is empty
        available(p) = 0;
        if ~any(available)
            break
        end

        [~,~,ngh] = find(available(neighbors(C,p)));

        if ~isempty(ngh)
            idx = randi(length(ngh));  % Random choice.
            q = ngh(idx);              % Next cell.
            if length(ngh) > 1
                % Could have chosen another neighbor.
                branches(end+1) = p;
            end

            % Add a cell and remove a barrier.
            tree(end+1,:) = [p q];
            [i,j] = wall(p,q,nr);
            B = rmedge(B,i,j);

            % Show detail.
            if detail                
                highlight(Bp, i, j, ...
                     'LineStyle', 'none');
                highlight(Cp, p, q, ...
                    'EdgeColor', [0 .5 0], ...
                    'LineStyle', '-');
                drawnow; 
            end

            p = q;

        else
            
            for p = branches
                if all(available(neighbors(C,p)) == 0)
                    branches(branches==p) = [];
                end
            end

            % Take another branch.
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
    [~,Cp] = plotem(B,C,'none');

    if shortest
        
        [path,len] = shortestpath(C,1,nr^2);
        
        highlight(Cp,path, ...
            'edgecolor',[0 .5 0], ...
            'lineStyle','-', ...
            'nodecolor',[0 .5 0], ...
            'marker','o')
        highlight(Cp,[1 nr^2])
        title(['length = ' int2str(len)])
    end

    % -------------------------------------------------------------

    function [i,j] = wall(p,q,m)
        % Wall [i,j] blocks path [p,q].
        switch q-p
            case -m  % west
                i = p+ceil(p/m)-1;
                j = i+1;
            case -1  % north
                i = p+ceil(p/m)-1;
                j = i+n;
            case 1  % south
                i = p+ceil(p/m);
                j = i+n;
            case m  % east
                i = p+ceil(p/m)-1+n;
                j = i+1;
        end
    end

    function dg  = darkgreen
        dg = [0 .5 0];
    end

    % function [Bp,Cp] = plotem(B,C,Ccolor)
    %     % Plot both graphs
    %     if nargin < 3
    %         Ccolor = darkgreen;
    %     end
    %     if strcmp(Ccolor,'none')
    %         Ccolor = 'white';
    %         linestyle = 'none';
    %     else
    %         linestyle = '-';
    %     end
    %     if numedges(B) == 49
    %         % lab3 thumbnail
    %         lw = 1;
    %         ms = 1;
    %     elseif numedges(B) > 400
    %         lw = 2;
    %         ms = 2;
    %     else
    %         lw = 3;
    %         ms = 4;
    %     end
    % 
    %     k = (0:n^2-1)';
    %     Bp = plot(B,'XData',floor(k/n), ...
    %         'YData',mod(n-k-1,n), ...
    %         'linewidth',lw, ...
    %         'markersize',ms, ...
    %         'nodelabel',{});
    %     axis equal
    %     set(gca,'xtick',[],'ytick',[])
    % 
    %     hold on
    %     k = 1:nr^2;
    %     Cp = plot(C,'XData',floor((k-1)/nr)+0.5, ...
    %         'YData',mod(n-k-1,nr)+0.5, ...
    %         'NodeLabel',{}, ...
    %         'NodeColor',Ccolor, ...
    %         'LineStyle',linestyle, ...
    %         'EdgeColor','white', ...
    %         'linewidth',3);
    % 
    %     hold off
    %     drawnow
    % end
%end % amaze