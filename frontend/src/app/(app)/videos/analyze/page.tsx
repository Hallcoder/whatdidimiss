"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Upload, UploadCloud } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAnalyzeVideo, useUploadVideo } from "@/lib/hooks/use-videos";
import { toast } from "sonner";

export default function AnalyzePage() {
  return (
    <div className="mx-auto max-w-lg space-y-6">
      <Link
        href="/videos"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Videos
      </Link>

      <Card>
        <CardHeader>
          <CardTitle>Analyze a Video</CardTitle>
          <CardDescription>
            Paste a YouTube URL or upload a video file to get AI-powered coaching insights.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="url">
            <TabsList className="mb-4 w-full">
              <TabsTrigger value="url">YouTube URL</TabsTrigger>
              <TabsTrigger value="upload">Upload Video</TabsTrigger>
            </TabsList>
            <TabsContent value="url">
              <YouTubeUrlTab />
            </TabsContent>
            <TabsContent value="upload">
              <UploadTab />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

function YouTubeUrlTab() {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();
  const mutation = useAnalyzeVideo();

  const youtubeRegex =
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)[\w-]{11}/;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!youtubeRegex.test(url)) {
      setError("Please enter a valid YouTube URL.");
      return;
    }

    mutation.mutate(url, {
      onSuccess: (data) => {
        toast.success("Video submitted for analysis");
        router.push(`/dashboard/${data.video_id}`);
      },
      onError: (err: unknown) => {
        const msg =
          (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data
            ?.error?.message ?? "Failed to submit video for analysis.";
        setError(msg);
        toast.error(msg);
      },
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Input
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={mutation.isPending}
        />
        {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      </div>
      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending ? "Submitting..." : "Start Analysis"}
      </Button>
    </form>
  );
}

function UploadTab() {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { mutate, isPending, uploadProgress } = useUploadVideo();

  const acceptedTypes = ["video/mp4", "video/quicktime", "video/webm"];

  const handleFile = useCallback((file: File) => {
    setError("");
    if (!acceptedTypes.includes(file.type)) {
      setError("Unsupported file type. Please use mp4, mov, or webm.");
      return;
    }
    setSelectedFile(file);
  }, []);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedFile) return;

    mutate(
      { file: selectedFile, title: title || undefined },
      {
        onSuccess: (data) => {
          toast.success("Video uploaded and submitted for analysis");
          router.push(`/dashboard/${data.video_id}`);
        },
        onError: (err: unknown) => {
          const msg =
            (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data
              ?.error?.message ?? "Failed to upload video.";
          setError(msg);
          toast.error(msg);
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div
        className={`relative flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
          dragActive
            ? "border-primary bg-primary/5"
            : selectedFile
              ? "border-primary/50 bg-primary/5"
              : "border-border hover:border-primary/50"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/mp4,video/quicktime,video/webm"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        {selectedFile ? (
          <div className="text-center">
            <Upload className="mx-auto mb-2 h-8 w-8 text-primary" />
            <p className="text-sm font-medium">{selectedFile.name}</p>
            <p className="text-xs text-muted-foreground">
              {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
            </p>
          </div>
        ) : (
          <div className="text-center">
            <UploadCloud className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium">Drop a video file here or click to browse</p>
            <p className="text-xs text-muted-foreground">MP4, MOV, or WebM up to 500 MB</p>
          </div>
        )}
      </div>

      {selectedFile && (
        <Input
          placeholder="Video title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={isPending}
        />
      )}

      {isPending && uploadProgress > 0 && (
        <div className="space-y-1">
          <Progress value={uploadProgress} />
          <p className="text-center text-xs text-muted-foreground">
            Uploading... {uploadProgress}%
          </p>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button type="submit" className="w-full" disabled={!selectedFile || isPending}>
        {isPending ? "Uploading..." : "Upload & Analyze"}
      </Button>
    </form>
  );
}
