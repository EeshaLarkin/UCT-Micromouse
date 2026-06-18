syms xs ys ths vs ws bgzs baxs bays real
xvs = [xs ys ths vs ws bgzs baxs bays]';
xdfs = [vs*cos(ths) vs*sin(ths) ws 0 0 0 0 0]'
jacobian(xdfs,xvs)

xdotf = @(x)[x(4)*cos(x(3)) x(4)*sin(x(3)) x(5) 0 0 0 0 0]';
Jxdotf = @(x)[zeros(8,1) zeros(8,1) [-x(4)*sin(x(3)); x(4)*cos(x(3)); zeros(6,1)] ...
              [cos(x(3)); sin(x(3)); zeros(6,1)] [0; 0; 1; 0; 0; 0; 0; 0] zeros(8,3)];

x = [1 1 0.4 0.3 0 0 0 0]';
N = length(x);
iCx = diag([0.001*ones(5,1); 0.1*ones(3,1)]);  % initially stationary at known position
filter = trackingEKF(@mm_ekf_predict, @mm_ekf_meas, x, ...
                     'HasAdditiveProcessNoise', true, ...
                     'HasAdditiveMeasurementNoise', true);
initialize(filter, x, iCx);




fh = [];
for i=1:10
  T = 0.1;

  % Continuous-time state transition covariance
  Rth = [cos(x(3)) -sin(x(3)); sin(x(3)) cos(x(3))];
  std_v = 0.03;
  std_th = 0.01;
  std_thd = 0.01;
  std_vd = 0.03;
  std_wd = 0.01;
  std_bgd = 0.01;
  std_bad = 0.01;
  Q = zeros(N,N);
  Q(1:2,1:2) = Rth*diag([std_v std_th].^2)*Rth';
  Q(3:end,3:end) = diag([std_thd std_vd std_wd std_bgd std_bad std_bad].^2)

  % Approximation using expm(AT)=I+AT
  A = Jxdotf(x);
  Qd1 = T*Q + T^2/2*(Q*A'+A*Q) + T^3/3*A*Q*A'

  % Approximation using Riemannian sum
  Qd2 = zeros(N,N);
  ts = linspace(0,T,15);
  dtau = ts(2)-ts(1);
  for tau=ts(1:end-1)
    Qd2 = Qd2 + expm(A*tau)*Q*expm(A'*tau)*dtau;
  end

  






  xdot = xdotf(x);
  x = x + T*xdot;  % Very approximate

  fh = plotrobot(x(1),x(2),x(3),simstruct,fh);
  pause(0.05);
end

