% test_autograder.m
% Automated test suite for EEE3097S Micromouse Autograder

% 1. Set up path environment
autograder_dir = fileparts(mfilename('fullpath'));
root_dir = fileparts(autograder_dir);
addpath(autograder_dir);
addpath(fullfile(autograder_dir, 'mazes'));
addpath(fullfile(root_dir, 'simulator'));
addpath(fullfile(root_dir, 'models'));

% Clean database files to start fresh
db_dir = fullfile(autograder_dir, 'db');
if exist(db_dir, 'dir')
    rmdir(db_dir, 's');
end
mkdir(db_dir);

fprintf('=== STARTING AUTOGRADER TEST SUITE ===\n\n');

%% --- TEST 1: Valid Simulink Track Grading ---
fprintf('--- TEST 1: Grading a valid Simulink submission ---\n');
app = uct_autograder_app();
app.StudentID = 'STUDENT001';
app.SelectedTrack = 'Simulink Track';
app.UploadedFilePath = fullfile(root_dir, 'models', 'StudentTemplate.slx');

% Run grading
app.gradeCallback();

% Verify D2L gradebook update
assert(exist(app.GradesCsvPath, 'file') > 0, 'D2L grades file was not created.');
fid = fopen(app.GradesCsvPath, 'r');
csv_content = fread(fid, '*char')';
fclose(fid);
fprintf('Grades CSV Content:\n%s\n', csv_content);
assert(contains(csv_content, 'STUDENT001'), 'Student ID not found in D2L gradebook.');

% Verify submissions database
assert(isfield(app.SubmissionsDb, 'STUDENT001'), 'Submissions database entry not found.');
assert(strcmp(app.SubmissionsDb.STUDENT001.status, 'Completed') || strcmp(app.SubmissionsDb.STUDENT001.status, 'Crashed'), 'Status not updated.');
fprintf('Test 1: PASSED\n\n');

% Close app before next tests
delete(app);


%% --- TEST 2: Failsafe Port Check ---
fprintf('--- TEST 2: Grading a broken Simulink model ---\n');
% Create a copy of StudentTemplate and delete a critical port
broken_model_path = fullfile(autograder_dir, 'StudentTemplate_broken.slx');
if exist(broken_model_path, 'file')
    delete(broken_model_path);
end
copyfile(fullfile(root_dir, 'models', 'StudentTemplate.slx'), broken_model_path);

load_system(broken_model_path);
delete_block('StudentTemplate_broken/TOF_FRONT');
save_system('StudentTemplate_broken');
close_system('StudentTemplate_broken', 0);

app = uct_autograder_app();
app.StudentID = 'STUDENT002';
app.SelectedTrack = 'Simulink Track';
app.UploadedFilePath = broken_model_path;

% Run grading
app.gradeCallback();

% Verify the run failed with "Port Error" or "0% (Port Error)"
assert(strcmp(app.SubmissionsDb.STUDENT002.status, 'Port Error'), 'Status should be Port Error.');
assert(app.SubmissionsDb.STUDENT002.score == 0, 'Score should be 0% for port error.');
fprintf('Submissions DB entry for STUDENT002:\n');
disp(app.SubmissionsDb.STUDENT002);
fprintf('Test 2: PASSED\n\n');

% Clean up broken file
delete(broken_model_path);
delete(app);


%% --- TEST 3: Plagiarism Checker ---
fprintf('--- TEST 3: Checking Plagiarism Trigger ---\n');
app = uct_autograder_app();
app.StudentID = 'STUDENT003'; % Different student ID
app.SelectedTrack = 'Simulink Track';
app.UploadedFilePath = fullfile(root_dir, 'models', 'StudentTemplate.slx'); % Same file as STUDENT001

% Run grading
app.gradeCallback();

% Verify that the plagiarism flag is true in the database for the duplicate
assert(app.SubmissionsDb.STUDENT003.isPlagiarism == true, 'Plagiarism checker failed to flag duplicate submission.');
fprintf('Submissions DB entry for STUDENT003:\n');
disp(app.SubmissionsDb.STUDENT003);
fprintf('Test 3: PASSED\n\n');

delete(app);


%% --- TEST 4: Python Track Grading ---
fprintf('--- TEST 4: Grading a Python submission ---\n');

% Create a zip of the python code for testing
zip_file_path = fullfile(autograder_dir, 'student_python.zip');
if exist(zip_file_path, 'file')
    delete(zip_file_path);
end

% Create temporary zip directory
zip_temp_dir = fullfile(autograder_dir, 'zip_temp');
if exist(zip_temp_dir, 'dir')
    rmdir(zip_temp_dir, 's');
end
mkdir(zip_temp_dir);

% Copy python test files
repo_root = fileparts(root_dir);
copyfile(fullfile(repo_root, 'python', 'main.py'), fullfile(zip_temp_dir, 'main.py'));
copyfile(fullfile(repo_root, 'python', 'uct_mouse.py'), fullfile(zip_temp_dir, 'uct_mouse.py'));
copyfile(fullfile(repo_root, 'python', 'micromouse.py'), fullfile(zip_temp_dir, 'micromouse.py'));

zip(zip_file_path, '*', zip_temp_dir);
rmdir(zip_temp_dir, 's');

app = uct_autograder_app();
app.StudentID = 'STUDENT004';
app.SelectedTrack = 'Python Track';
app.UploadedFilePath = zip_file_path;

% Run grading
app.gradeCallback();

% Verify D2L gradebook update
fid = fopen(app.GradesCsvPath, 'r');
csv_content = fread(fid, '*char')';
fclose(fid);
fprintf('Grades CSV Content:\n%s\n', csv_content);
assert(contains(csv_content, 'STUDENT004'), 'Student ID not found in D2L gradebook.');

% Verify submissions database
assert(isfield(app.SubmissionsDb, 'STUDENT004'), 'Submissions database entry not found.');
assert(strcmp(app.SubmissionsDb.STUDENT004.status, 'Completed') || strcmp(app.SubmissionsDb.STUDENT004.status, 'Crashed'), 'Status not updated.');
fprintf('Test 4: PASSED\n\n');

% Clean up
delete(zip_file_path);
delete(app);

fprintf('=== ALL TESTS PASSED SUCCESSFULLY! ===\n');
exit;
