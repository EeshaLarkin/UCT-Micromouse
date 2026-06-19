% Helper script to configure models for auto-flashing on build
models = {'StudentTemplate', 'UCT_KDeploy'};
for i = 1:length(models)
    model = models{i};
    try
        load_system(model);
        set_param(model, 'PostCodeGenCommand', 'flash_micromouse(buildInfo)');
        save_system(model);
        fprintf('Configured %s.slx to auto-flash on build.\n', model);
    catch ME
        fprintf('Failed to configure %s: %s\n', model, ME.message);
    end
end
