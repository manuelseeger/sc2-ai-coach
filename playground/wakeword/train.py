from livekit.wakeword import (
    
    load_config,
    run_generate,
    run_augment,
    run_extraction,
    run_train,
    run_export,
    run_eval,
)

# Load from YAML or construct directly
config = load_config("train_config.yaml")


# Run individual stages
print("Generating synthetic data...")
run_generate(config)     # TTS synthesis + adversarial negatives
print("Augmenting data...")
run_augment(config)      # Add noise, reverb, pitch shifts
print("Extracting features...")
run_extraction(config)   # Extract mel spectrograms + speech embeddings → .npy
print("Training model...")
run_train(config)        # 3-phase adaptive training
print("Exporting model to ONNX...")
onnx_path = run_export(config)       # Export to ONNX

# Evaluate the exported model
results = run_eval(config, onnx_path)
print(f"AUT={results['aut']:.4f}  FPPH={results['fpph']:.2f}  Recall={results['recall']:.1%}")