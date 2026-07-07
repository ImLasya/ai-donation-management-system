import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  CameraOff,
  RefreshCw,
  Upload,
  X,
  Image as ImageIcon,
  SwitchCamera,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type Status = "idle" | "starting" | "streaming" | "denied" | "unavailable" | "captured";

export function CameraCapture({ onCapture }: { onCapture: (dataUrl: string) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [facing, setFacing] = useState<"environment" | "user">("environment");
  const [preview, setPreview] = useState<string | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const start = useCallback(
    async (mode: "environment" | "user" = facing) => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setStatus("unavailable");
        return;
      }
      setStatus("starting");
      stop();
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: mode },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setStatus("streaming");
      } catch (err) {
        const errorName = err instanceof Error ? err.name : "";
        setStatus(errorName === "NotAllowedError" ? "denied" : "unavailable");
      }
    },
    [facing, stop],
  );

  useEffect(() => () => stop(), [stop]);

  const capture = () => {
    const video = videoRef.current,
      canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    const url = canvas.toDataURL("image/jpeg", 0.9);
    setPreview(url);
    setStatus("captured");
    stop();
  };

  const switchCam = () => {
    const next = facing === "environment" ? "user" : "environment";
    setFacing(next);
    start(next);
  };

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setPreview(reader.result as string);
      setStatus("captured");
      stop();
    };
    reader.readAsDataURL(file);
  };

  const retake = () => {
    setPreview(null);
    start();
  };

  return (
    <Card className="overflow-hidden p-0">
      <div className="relative aspect-video w-full bg-foreground/90">
        <video
          ref={videoRef}
          playsInline
          muted
          className={`h-full w-full object-cover ${status === "streaming" ? "block" : "hidden"}`}
        />
        <canvas ref={canvasRef} className="hidden" />

        {status === "captured" && preview && (
          <img
            src={preview}
            alt="Captured donation items"
            className="h-full w-full object-contain"
          />
        )}

        {(status === "idle" || status === "starting") && (
          <div className="absolute inset-0 grid place-items-center text-center text-primary-foreground">
            <div>
              <Camera className="mx-auto h-12 w-12 opacity-70" />
              <p className="mt-3 text-sm opacity-80">
                {status === "starting" ? "Starting camera…" : "Camera is off"}
              </p>
            </div>
          </div>
        )}
        {status === "denied" && (
          <div className="absolute inset-0 grid place-items-center px-6 text-center text-primary-foreground">
            <div>
              <CameraOff className="mx-auto h-12 w-12 text-destructive" />
              <p className="mt-3 font-semibold">Camera permission denied</p>
              <p className="mt-1 text-sm opacity-80">
                Enable camera access in your browser settings, or upload an image instead.
              </p>
            </div>
          </div>
        )}
        {status === "unavailable" && (
          <div className="absolute inset-0 grid place-items-center px-6 text-center text-primary-foreground">
            <div>
              <CameraOff className="mx-auto h-12 w-12 opacity-70" />
              <p className="mt-3 font-semibold">No camera available</p>
              <p className="mt-1 text-sm opacity-80">Upload an image of your items to continue.</p>
            </div>
          </div>
        )}

        {status === "streaming" && (
          <div className="pointer-events-none absolute inset-6 rounded-xl border-2 border-dashed border-primary-foreground/50" />
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 p-4">
        {status !== "streaming" && status !== "captured" && (
          <Button onClick={() => start()} className="gap-2">
            <Camera className="h-4 w-4" /> Start Camera
          </Button>
        )}
        {status === "streaming" && (
          <>
            <Button onClick={capture} className="gap-2">
              <ImageIcon className="h-4 w-4" /> Capture Photo
            </Button>
            <Button variant="outline" onClick={switchCam} className="gap-2">
              <SwitchCamera className="h-4 w-4" /> Switch
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                stop();
                setStatus("idle");
              }}
              className="gap-2"
            >
              <X className="h-4 w-4" /> Stop
            </Button>
          </>
        )}
        {status === "captured" && (
          <>
            <Button variant="outline" onClick={retake} className="gap-2">
              <RefreshCw className="h-4 w-4" /> Retake
            </Button>
            <Button onClick={() => preview && onCapture(preview)} className="gap-2">
              Analyze Items
            </Button>
          </>
        )}
        <div className="ml-auto">
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFile} />
          <Button variant="ghost" onClick={() => fileRef.current?.click()} className="gap-2">
            <Upload className="h-4 w-4" /> Upload Image
          </Button>
        </div>
      </div>
    </Card>
  );
}
