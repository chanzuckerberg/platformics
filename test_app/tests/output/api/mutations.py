"""
GraphQL mutations for files and entities

Auto-generated by running 'make codegen'. Do not edit.
Make changes to the template codegen/templates/api/mutations.py.j2 instead.
"""

import strawberry
from typing import Sequence
from api.files import (
    File,
    create_file,
    upload_file,
    mark_upload_complete,
    concatenate_files,
    SignedURL,
    MultipartUploadResponse,
)
from api.types.sample import Sample, create_sample, update_sample, delete_sample
from api.types.sequencing_read import (
    SequencingRead,
    create_sequencing_read,
    update_sequencing_read,
    delete_sequencing_read,
)
from api.types.genomic_range import GenomicRange, create_genomic_range, update_genomic_range, delete_genomic_range
from api.types.contig import Contig, create_contig, update_contig, delete_contig


@strawberry.type
class Mutation:
    # File mutations
    create_file: File = create_file
    upload_file: MultipartUploadResponse = upload_file
    mark_upload_complete: File = mark_upload_complete
    concatenate_files: SignedURL = concatenate_files

    # Sample mutations
    create_sample: Sample = create_sample
    update_sample: Sequence[Sample] = update_sample
    delete_sample: Sequence[Sample] = delete_sample

    # SequencingRead mutations
    create_sequencing_read: SequencingRead = create_sequencing_read
    update_sequencing_read: Sequence[SequencingRead] = update_sequencing_read
    delete_sequencing_read: Sequence[SequencingRead] = delete_sequencing_read

    # GenomicRange mutations
    create_genomic_range: GenomicRange = create_genomic_range
    update_genomic_range: Sequence[GenomicRange] = update_genomic_range
    delete_genomic_range: Sequence[GenomicRange] = delete_genomic_range

    # Contig mutations
    create_contig: Contig = create_contig
    update_contig: Sequence[Contig] = update_contig
    delete_contig: Sequence[Contig] = delete_contig