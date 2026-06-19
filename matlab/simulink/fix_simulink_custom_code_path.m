% Script to check and fix custom code paths in Simulink models
models = {'StudentTemplate', 'UCT_KDeploy'};

for i = 1:length(models)
    model = models{i};
    try
        load_system(model);
        
        % Check Code Generation Custom Code parameters
        src = get_param(model, 'CustomSource');
        inc = get_param(model, 'CustomInclude');
        
        fprintf('\n--- Checking %s.slx ---\n', model);
        
        changed = false;
        
        % Fix CustomSource path (convert ../ to ../../ if needed)
        if contains(src, '../src/kernel/src/simulink_wrapper.c') && ~contains(src, '../../src/kernel/src/simulink_wrapper.c')
            new_src = strrep(src, '../src/kernel/src/simulink_wrapper.c', '../../src/kernel/src/simulink_wrapper.c');
            set_param(model, 'CustomSource', new_src);
            fprintf('Fixed CustomSource -> %s\n', new_src);
            changed = true;
        end
        
        % Fix CustomInclude path
        if contains(inc, '../src/kernel/inc') && ~contains(inc, '../../src/kernel/inc')
            new_inc = strrep(inc, '../src/kernel/inc', '../../src/kernel/inc');
            set_param(model, 'CustomInclude', new_inc);
            fprintf('Fixed CustomInclude -> %s\n', new_inc);
            changed = true;
        end
        
        % Check Simulation Target Custom Code parameters
        sim_src = get_param(model, 'SimUserSources');
        sim_inc = get_param(model, 'SimUserIncludeDirs');
        
        % Fix SimUserSources path
        if contains(sim_src, '../src/kernel/src/simulink_wrapper.c') && ~contains(sim_src, '../../src/kernel/src/simulink_wrapper.c')
            new_sim_src = strrep(sim_src, '../src/kernel/src/simulink_wrapper.c', '../../src/kernel/src/simulink_wrapper.c');
            set_param(model, 'SimUserSources', new_sim_src);
            fprintf('Fixed SimUserSources -> %s\n', new_sim_src);
            changed = true;
        end
        
        % Fix SimUserIncludeDirs path
        if contains(sim_inc, '../src/kernel/inc') && ~contains(sim_inc, '../../src/kernel/inc')
            new_sim_inc = strrep(sim_inc, '../src/kernel/inc', '../../src/kernel/inc');
            set_param(model, 'SimUserIncludeDirs', new_sim_inc);
            fprintf('Fixed SimUserIncludeDirs -> %s\n', new_sim_inc);
            changed = true;
        end
        
        if changed
            save_system(model);
            fprintf('Success! Saved updated %s.slx\n', model);
        else
            fprintf('No relative custom code path issues found in %s.slx\n', model);
        end
    catch ME
        fprintf('Failed to process %s: %s\n', model, ME.message);
    end
end
