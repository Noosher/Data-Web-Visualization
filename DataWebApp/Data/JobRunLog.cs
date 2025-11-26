using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace DataWebApp.data;

[Table("job_run_log")]
[Index("LastRunAt", Name = "idx_job_run_last_run_at", AllDescending = true)]
public partial class JobRunLog
{
    [Key]
    [Column("job_name")]
    public string JobName { get; set; } = null!;

    [Column("last_run_at")]
    public DateTime? LastRunAt { get; set; }

    [Column("last_status")]
    public string? LastStatus { get; set; }

    [Column("details", TypeName = "jsonb")]
    public string? Details { get; set; }
}
