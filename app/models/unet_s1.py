"""Arquitetura usada pelo checkpoint Sentinel-1 recebido."""

def build_unet_s1(in_channels: int = 2, num_classes: int = 3):
    try:
        import segmentation_models_pytorch as smp
    except ImportError as exc:
        raise RuntimeError(
            "Dependência ausente: segmentation-models-pytorch. "
            "Instale com: pip install -r requirements.txt"
        ) from exc

    return smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None,
        in_channels=in_channels,
        classes=num_classes,
    )
