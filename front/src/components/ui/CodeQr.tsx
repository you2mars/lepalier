"use client";
// Code QR (image SVG en data:, permise par la politique de sécurité), toujours avec son texte de remplacement.
import QRCode from "qrcode";
import { useEffect, useState } from "react";

export function CodeQr({ valeur, alt }: { valeur: string; alt: string }) {
  const [image, setImage] = useState<string>();

  useEffect(() => {
    let actif = true;
    void QRCode.toString(valeur, { type: "svg", errorCorrectionLevel: "M", margin: 2 }).then((svg) => {
      if (actif) setImage(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`);
    });
    return () => {
      actif = false;
    };
  }, [valeur]);

  return image ? <img className="qr" src={image} alt={alt} width={200} height={200} /> : null;
}
