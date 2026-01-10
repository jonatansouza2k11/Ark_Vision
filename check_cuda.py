import torch

print("torch.__version__:", torch.__version__)
print("torch.version.cuda:", torch.version.cuda)
print("CUDA disponível:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("device_count:", torch.cuda.device_count())
    print("GPU 0:", torch.cuda.get_device_name(0))
else:
    try:
        torch.ones(1).cuda()
    except Exception as e:
        print("Erro ao mover tensor para CUDA:", repr(e))
