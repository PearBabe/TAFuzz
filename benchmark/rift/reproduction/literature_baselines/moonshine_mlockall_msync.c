/*
 * Faithful, self-contained form of MoonShine Figure 2.
 *
 * This is not Linux kernel source and is not the unpublished MoonShine Smatch
 * checker.  It exists solely to make the paper's W(writer) intersection
 * R_cond(reader) rule executable with a modern Clang AST.
 */

enum {
    MS_INVALIDATE = 1,
    VM_LOCKED = 2,
    EBUSY = 16,
};

struct vm_area_struct {
    unsigned int vm_flags;
};

static void mlock_fixup_lock(struct vm_area_struct *vma,
                             unsigned int newflags,
                             int lock) {
    if (lock) {
        vma->vm_flags = newflags;
    }
}

int mlockall(struct vm_area_struct *vma, unsigned int newflags, int lock) {
    mlock_fixup_lock(vma, newflags, lock);
    return 0;
}

int msync(struct vm_area_struct *vma, unsigned int flags) {
    if ((flags & MS_INVALIDATE) && (vma->vm_flags & VM_LOCKED)) {
        return -EBUSY;
    }
    return 0;
}

int unrelated_call(struct vm_area_struct *vma) {
    return (int)vma->vm_flags;
}
